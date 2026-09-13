import { memo, useMemo, useState } from "react";
import { Users } from "lucide-react";
import type { Opportunity } from "@/core/types";
import { Button, Chip } from "@/core/ui";
import {
  SCORE_TONE,
  applicationStatusLabel,
  archetypeLabel,
  daysLeft,
  recommendationLabel,
  recommendationTone,
  remoteKind,
  scoreBand,
  statusLabel,
} from "./labels";

interface OpportunityKanbanProps {
  items: Opportunity[];
  disabled?: boolean;
  onOpen: (id: string) => void;
  onStatus: (id: string, status: string) => void;
  /** Pano, seçili çalışma alanının yaşam döngüsünü gösterir. */
  section: "jobs" | "announcements";
}

interface ColumnDef {
  key: string;
  title: string;
  statuses: string[];
  tone?: "accent" | "ok" | "warn" | "danger" | "neutral";
}

const JOB_COLUMNS: ColumnDef[] = [
  { key: "discovered", title: "Keşfedildi", statuses: ["discovered"], tone: "neutral" },
  { key: "shortlisted", title: "Kısa listede", statuses: ["shortlisted"], tone: "accent" },
  { key: "dismissed", title: "Elendi", statuses: ["dismissed"], tone: "neutral" },
  { key: "archived", title: "Arşivde", statuses: ["archived", "closed"], tone: "neutral" },
];

const ANNOUNCEMENT_COLUMNS: ColumnDef[] = [
  { key: "new", title: "Yeni", statuses: ["new"], tone: "accent" },
  { key: "reviewed", title: "İncelendi", statuses: ["reviewed"], tone: "neutral" },
  { key: "watching", title: "Takipte", statuses: ["watching"], tone: "warn" },
  {
    key: "action_required",
    title: "Aksiyon gerekli",
    statuses: ["action_required"],
    tone: "warn",
  },
  { key: "applied", title: "Başvuruldu", statuses: ["applied", "completed"], tone: "ok" },
  { key: "closed", title: "Süresi geçti / arşiv", statuses: ["expired", "archived"], tone: "neutral" },
];

const INITIAL_LIMIT = 40;

interface KanbanCardProps {
  item: Opportunity;
  disabled: boolean;
  onOpen: (id: string) => void;
  onStatus: (id: string, status: string) => void;
  primaryStatus: string;
}

const KanbanCard = memo(function KanbanCard({ item, disabled, onOpen, onStatus, primaryStatus }: KanbanCardProps) {
  const band = scoreBand(item.score ?? null);
  const tone = band ? SCORE_TONE[band] : "neutral";
  const left = daysLeft(item.deadline_at ?? null);
  const remote = remoteKind(item.remote);
  // Yalnızca backend'in izin verdiği geçişler düğme olur.
  const allowed = item.allowed_transitions ?? [];

  return (
    // Kart bir kapsayıcıdır, tıklanabilir "role=button" DEĞİL: içinde gerçek
    // düğmeler var. Açma işi başlıktaki gerçek <button>'a aittir.
    <article className="group rounded-control border border-subtle bg-canvas p-3 shadow-card transition hover:border-strong hover:shadow-overlay">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="truncate text-meta font-medium text-secondary">{item.organization || "Bilinmeyen kurum"}</span>
        {item.score !== null && item.score !== undefined && (
          <Chip tone={tone}>{band === "eliminated" ? "Elendi" : `${item.score.toFixed(0)}p`}</Chip>
        )}
      </div>

      <button
        type="button"
        onClick={() => onOpen(item.id)}
        className="mb-2 line-clamp-2 w-full text-left text-body font-medium text-primary transition hover:text-accent"
      >
        {item.title}
      </button>

      <div className="mb-3 flex flex-wrap items-center gap-1.5 text-micro">
        {remote && remote !== "unknown" && (
          <Chip tone="neutral">{remote === "remote" ? "Remote" : remote === "hybrid" ? "Hybrid" : "Ofis"}</Chip>
        )}
        {left !== null && (
          <Chip tone={left <= 3 ? "danger" : "warn"}>
            {left < 0 ? "Süresi geçti" : left === 0 ? "Son gün" : `${left}g kaldı`}
          </Chip>
        )}
        {item.profile_match_ratio !== null && item.profile_match_ratio !== undefined && (
          <Chip tone="ok">Profil: %{Math.round(item.profile_match_ratio * 100)}</Chip>
        )}
        {item.application_status && <Chip tone="accent">Başvuru: {statusLabel(item.application_status)}</Chip>}
        {item.evaluation?.recommendation && (
          <Chip tone={recommendationTone(item.evaluation.recommendation)}>
            {recommendationLabel(item.evaluation.recommendation)} · {item.evaluation.score}p
          </Chip>
        )}
        {item.evaluation?.archetype && <Chip tone="neutral">{archetypeLabel(item.evaluation.archetype)}</Chip>}
        {item.intelligence?.connection_count ? (
          <Chip tone="accent">
            <span className="inline-flex items-center gap-1">
              <Users size={11} /> {item.intelligence.connection_count} bağlantı
            </span>
          </Chip>
        ) : null}
        {item.intelligence?.is_repost && <Chip tone="warn">Tekrar ilan · {item.intelligence.repost_count}</Chip>}
        {item.intelligence?.pay_transparency_risk && <Chip tone="warn">Geniş ücret bandı</Chip>}
        {item.intelligence?.geo_mismatch && <Chip tone="danger">Konum uyuşmazlığı</Chip>}
        {item.status !== primaryStatus && <Chip tone="accent">{statusLabel(item.status)}</Chip>}
      </div>

      {allowed.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 border-t border-subtle pt-2">
          {allowed.slice(0, 3).map((status) => (
            <Button
              key={status}
              size="sm"
              variant={status === "dismissed" || status === "expired" ? "ghost" : "secondary"}
              disabled={disabled}
              onClick={() => onStatus(item.id, status)}
              title={`${statusLabel(item.status)} → ${statusLabel(status)}`}
            >
              {statusLabel(status)}
            </Button>
          ))}
        </div>
      )}
    </article>
  );
});

export function OpportunityKanban({ items, disabled = false, onOpen, onStatus, section }: OpportunityKanbanProps) {
  const [limits, setLimits] = useState<Record<string, number>>({});
  const columns = section === "jobs" ? JOB_COLUMNS : ANNOUNCEMENT_COLUMNS;

  const grouped = useMemo(() => {
    const map = new Map<string, Opportunity[]>();
    for (const column of columns) map.set(column.key, []);
    for (const item of items) {
      const column = columns.find((candidate) => candidate.statuses.includes(item.status));
      map.get(column?.key ?? columns[0].key)?.push(item);
    }
    return map;
  }, [items, columns]);

  return (
    <div className="flex gap-4 overflow-x-auto pb-4 pt-1" role="region" aria-label="Fırsat kanban panosu">
      {columns.map((column) => {
        const columnItems = grouped.get(column.key) ?? [];
        const limit = limits[column.key] ?? INITIAL_LIMIT;
        const visible = columnItems.slice(0, limit);
        const remaining = columnItems.length - limit;

        return (
          <div
            key={column.key}
            className="flex w-72 shrink-0 flex-col rounded-card border border-subtle bg-surface-sunken/40"
          >
            <div className="flex items-center justify-between border-b border-subtle px-3 py-2.5">
              <div className="flex items-center gap-2">
                <span className="text-meta font-medium text-primary">{column.title}</span>
                <Chip tone={column.tone ?? "neutral"}>{columnItems.length}</Chip>
              </div>
            </div>

            <div className="flex max-h-[calc(100vh-220px)] flex-1 flex-col gap-2.5 overflow-y-auto p-2.5">
              {columnItems.length === 0 ? (
                <div className="flex h-24 items-center justify-center rounded-control border border-dashed border-subtle text-meta text-muted">
                  Bu aşamada kayıt yok
                </div>
              ) : (
                <>
                  {visible.map((item) => (
                    <KanbanCard
                      key={item.id}
                      item={item}
                      disabled={disabled}
                      onOpen={onOpen}
                      onStatus={onStatus}
                      primaryStatus={column.statuses[0]}
                    />
                  ))}
                  {remaining > 0 && (
                    <Button
                      onClick={() => setLimits((prev) => ({ ...prev, [column.key]: limit + INITIAL_LIMIT }))}
                      className="w-full"
                    >
                      + {remaining} daha fazla göster
                    </Button>
                  )}
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
