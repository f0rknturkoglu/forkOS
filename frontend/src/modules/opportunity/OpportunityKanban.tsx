import { useMemo } from "react";
import { Eye, XCircle } from "lucide-react";
import type { Opportunity } from "@/core/types";
import { Chip } from "@/core/ui";
import { SCORE_TONE, daysLeft, remoteKind, scoreBand, statusLabel } from "./labels";

interface OpportunityKanbanProps {
  items: Opportunity[];
  disabled?: boolean;
  onOpen: (id: string) => void;
  onStatus: (id: string, status: string) => void;
}

interface ColumnDef {
  key: string;
  title: string;
  statuses: string[];
  tone?: "accent" | "ok" | "warn" | "danger" | "neutral";
}

const COLUMNS: ColumnDef[] = [
  { key: "discovered", title: "Keşfedildi", statuses: ["discovered"], tone: "neutral" },
  { key: "considering", title: "İnceleniyor", statuses: ["considering", "preparing"], tone: "accent" },
  { key: "applied", title: "Başvuruldu", statuses: ["applied"], tone: "warn" },
  { key: "interview", title: "Mülakat", statuses: ["interview"], tone: "accent" },
  { key: "offer", title: "Teklif", statuses: ["offer"], tone: "ok" },
  { key: "terminal", title: "Sonuçlandı", statuses: ["accepted", "rejected", "withdrawn", "closed"], tone: "neutral" },
];

export function OpportunityKanban({ items, disabled = false, onOpen, onStatus }: OpportunityKanbanProps) {
  const grouped = useMemo(() => {
    const map = new Map<string, Opportunity[]>();
    for (const col of COLUMNS) {
      map.set(col.key, []);
    }
    for (const item of items) {
      const col = COLUMNS.find((c) => c.statuses.includes(item.status));
      if (col) {
        map.get(col.key)?.push(item);
      } else {
        map.get("discovered")?.push(item);
      }
    }
    return map;
  }, [items]);

  return (
    <div className="flex gap-4 overflow-x-auto pb-4 pt-1" role="region" aria-label="Fırsat kanban panosu">
      {COLUMNS.map((col) => {
        const colItems = grouped.get(col.key) ?? [];
        return (
          <div
            key={col.key}
            className="flex w-72 shrink-0 flex-col rounded-card border border-subtle bg-surface-sunken/40"
          >
            {/* Sütun Başlığı */}
            <div className="flex items-center justify-between border-b border-subtle px-3 py-2.5">
              <div className="flex items-center gap-2">
                <span className="text-meta font-medium text-primary">{col.title}</span>
                <Chip tone={col.tone ?? "neutral"}>{colItems.length}</Chip>
              </div>
            </div>

            {/* Sütun İçeriği */}
            <div className="flex flex-1 flex-col gap-2.5 overflow-y-auto p-2.5 max-h-[calc(100vh-220px)]">
              {colItems.length === 0 ? (
                <div className="flex h-24 items-center justify-center rounded-control border border-dashed border-subtle text-meta text-muted">
                  Bu aşamada kayıt yok
                </div>
              ) : (
                colItems.map((item) => {
                  const band = scoreBand(item.score ?? null);
                  const tone = band ? SCORE_TONE[band] : "neutral";
                  const left = daysLeft(item.deadline_at ?? null);
                  const remote = remoteKind(item.remote);

                  return (
                    <div
                      key={item.id}
                      onClick={() => onOpen(item.id)}
                      className="group cursor-pointer rounded-control border border-subtle bg-canvas p-3 shadow-card transition hover:border-strong hover:shadow-overlay"
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onOpen(item.id);
                        }
                      }}
                    >
                      {/* Üst bilgi: Şirket ve Skor */}
                      <div className="mb-1.5 flex items-center justify-between gap-2">
                        <span className="truncate text-meta font-medium text-secondary">
                          {item.organization || "Bilinmeyen kurum"}
                        </span>
                        {item.score !== null && item.score !== undefined && (
                          <Chip tone={tone}>{band === "killed" ? "Elendi" : `${item.score.toFixed(0)}p`}</Chip>
                        )}
                      </div>

                      {/* Başlık */}
                      <h4 className="mb-2 line-clamp-2 text-body font-medium text-primary">{item.title}</h4>

                      {/* Etiketler */}
                      <div className="mb-3 flex flex-wrap items-center gap-1.5 text-micro">
                        {remote && remote !== "unknown" && (
                          <Chip tone="neutral">
                            {remote === "remote" ? "Remote" : remote === "hybrid" ? "Hybrid" : "Ofis"}
                          </Chip>
                        )}
                        {left !== null && (
                          <Chip tone={left <= 3 ? "danger" : "warn"}>
                            {left < 0 ? "Süresi geçti" : left === 0 ? "Son gün" : `${left}g kaldı`}
                          </Chip>
                        )}
                        {item.skill_match && (
                          <Chip tone="ok">CV Uyumu: %{Math.round(item.skill_match.match_ratio * 100)}</Chip>
                        )}
                        {item.status !== col.statuses[0] && <Chip tone="accent">{statusLabel(item.status)}</Chip>}
                      </div>

                      {/* Hızlı Aksiyonlar */}
                      <div
                        className="flex items-center justify-between border-t border-subtle pt-2"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          type="button"
                          onClick={() => onOpen(item.id)}
                          className="flex items-center gap-1 text-micro text-secondary hover:text-primary"
                        >
                          <Eye size={12} />
                          Detay
                        </button>

                        <div className="flex items-center gap-1">
                          {item.status === "discovered" && (
                            <button
                              type="button"
                              disabled={disabled}
                              onClick={() => onStatus(item.id, "considering")}
                              className="rounded-control bg-accent-surface px-2 py-0.5 text-micro font-medium text-accent hover:bg-accent hover:text-canvas"
                              title="İncelemeye al"
                            >
                              İncele →
                            </button>
                          )}
                          {(item.status === "considering" || item.status === "preparing") && (
                            <button
                              type="button"
                              disabled={disabled}
                              onClick={() => onStatus(item.id, "applied")}
                              className="rounded-control bg-warn-surface px-2 py-0.5 text-micro font-medium text-warn hover:bg-warn hover:text-canvas"
                              title="Başvuruldu olarak işaretle"
                            >
                              Başvuruldu →
                            </button>
                          )}
                          {item.status === "applied" && (
                            <button
                              type="button"
                              disabled={disabled}
                              onClick={() => onStatus(item.id, "interview")}
                              className="rounded-control bg-accent-surface px-2 py-0.5 text-micro font-medium text-accent hover:bg-accent hover:text-canvas"
                              title="Mülakata taşı"
                            >
                              Mülakat →
                            </button>
                          )}
                          {item.status === "interview" && (
                            <button
                              type="button"
                              disabled={disabled}
                              onClick={() => onStatus(item.id, "offer")}
                              className="rounded-control bg-ok-surface px-2 py-0.5 text-micro font-medium text-ok hover:bg-ok hover:text-canvas"
                              title="Teklif aşamasına taşı"
                            >
                              Teklif →
                            </button>
                          )}
                          {item.status === "offer" && (
                            <button
                              type="button"
                              disabled={disabled}
                              onClick={() => onStatus(item.id, "accepted")}
                              className="rounded-control bg-ok-surface px-2 py-0.5 text-micro font-medium text-ok hover:bg-ok hover:text-canvas"
                              title="Teklifi kabul et"
                            >
                              Kabul ✓
                            </button>
                          )}
                          {!["accepted", "rejected", "withdrawn", "closed"].includes(item.status) && (
                            <button
                              type="button"
                              disabled={disabled}
                              onClick={() => onStatus(item.id, "rejected")}
                              className="rounded-control px-1.5 py-0.5 text-micro text-muted hover:bg-danger-surface hover:text-danger"
                              title="Reddedildi olarak işaretle"
                            >
                              <XCircle size={13} />
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
