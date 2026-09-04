import { useQuery } from "@tanstack/react-query";
import { CalendarClock, ArrowRight, Radar } from "lucide-react";
import { api } from "@/core/api";
import { Chip, Empty, Section, cx, relativeTime } from "@/core/ui";
import type { ApplicationFunnel, Followup, SilentApplication } from "@/core/types";
import { STATUS_TONES, statusLabel } from "./labels";

interface ApplicationCrmPanelProps {
  onSelect?: (id: string) => void;
  onStatusFilter?: (status: string) => void;
}

/** Basvuru CRM ozeti: funnel, donusum oranlari, red nedenleri, yaklasan takipler. */
export function ApplicationCrmPanel({ onSelect, onStatusFilter }: ApplicationCrmPanelProps = {}) {
  const { data: funnel } = useQuery({
    queryKey: ["applications-funnel"],
    queryFn: () => api.get<ApplicationFunnel>("/applications/funnel"),
    refetchInterval: 60_000,
  });
  const { data: followups = [] } = useQuery({
    queryKey: ["followups"],
    queryFn: () => api.get<Followup[]>("/opportunities/followups"),
  });
  const { data: silentApplications = [] } = useQuery({
    queryKey: ["opportunity-silence"],
    queryFn: () => api.get<SilentApplication[]>("/opportunities/silence?days=21"),
  });

  const total = funnel?.total ?? 0;
  const conv = funnel?.conversions ?? {};
  const maxCount = Math.max(1, ...(funnel?.by_status.map((r) => r.count) ?? [1]));

  return (
    <div className="space-y-4">
      <Section title="Başvuru funnel">
        {total === 0 ? (
          <Empty>Henüz başvuru yok — ilanlardan "Başvur" ile başla.</Empty>
        ) : (
          <div className="space-y-2">
            {funnel!.by_status.map((row) => {
              const tone = STATUS_TONES[row.status] ?? "neutral";
              return (
                <button
                  type="button"
                  key={row.status}
                  onClick={() => onStatusFilter?.(row.status)}
                  className="flex w-full items-center gap-3 rounded-control p-1 text-left transition hover:bg-surface-hover"
                  title={`${statusLabel(row.status)} durumundaki ilanları filtrele`}
                >
                  <span className="w-28 shrink-0 truncate text-meta text-secondary">{statusLabel(row.status)}</span>
                  <div className="h-4 min-w-0 flex-1 overflow-hidden rounded-control bg-surface-sunken">
                    <div
                      className={cx(
                        "h-full rounded-control transition-all",
                        tone === "ok"
                          ? "bg-ok"
                          : tone === "danger"
                            ? "bg-danger"
                            : tone === "warn"
                              ? "bg-warn"
                              : "bg-accent",
                      )}
                      style={{ width: (row.count / maxCount) * 100 + "%" }}
                    />
                  </div>
                  <span className="w-10 shrink-0 text-right text-meta tabular-nums font-medium text-primary">
                    {row.count}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </Section>

      <Section title="Dönüşüm oranları">
        {total === 0 ? (
          <Empty>Veri yok.</Empty>
        ) : (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {[
              ["applied_to_interview", "Başvuru → Görüşme"],
              ["interview_to_offer", "Görüşme → Teklif"],
              ["offer_to_accepted", "Teklif → Kabul"],
              ["applied_to_rejected", "Başvuru → Red"],
            ].map(([key, label]) => (
              <div key={key} className="rounded-control border border-subtle bg-surface-sunken/30 px-3 py-2">
                <div className="text-title leading-tight tabular-nums font-semibold text-primary">
                  {conv[key] == null ? "—" : conv[key] + "%"}
                </div>
                <div className="text-meta text-muted">{label}</div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Red nedenleri">
        {(funnel?.rejection_reasons ?? []).length === 0 ? (
          <Empty>Henüz red kaydı yok.</Empty>
        ) : (
          <ul className="space-y-1.5">
            {funnel!.rejection_reasons.map((row) => (
              <li key={row.reason} className="flex items-center gap-2 text-meta">
                <span className="h-1.5 w-1.5 rounded-full bg-danger" />
                <span className="text-secondary">{row.reason}</span>
                <Chip tone="danger">{row.count}</Chip>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Yaklaşan takipler" action={<CalendarClock size={14} className="text-icon" />}>
        {followups.length === 0 ? (
          <Empty>Takipli başvuru yok.</Empty>
        ) : (
          <ul className="space-y-1.5">
            {followups.slice(0, 8).map((f) => (
              <li key={f.id}>
                <button
                  type="button"
                  onClick={() => onSelect?.(f.id)}
                  className="group flex w-full items-center gap-2 rounded-control border border-subtle bg-surface px-3 py-2 text-left transition hover:border-strong hover:bg-surface-hover"
                >
                  <span className="min-w-0 flex-1 truncate text-body text-primary font-medium">{f.title}</span>
                  <Chip tone="warn">{relativeTime(f.follow_up_at)}</Chip>
                  <ArrowRight
                    size={13}
                    className="shrink-0 text-muted transition group-hover:translate-x-0.5 group-hover:text-primary"
                  />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Firma sessizliği" action={<Radar size={14} className="text-icon" />}>
        {silentApplications.length === 0 ? (
          <Empty>21 günü aşan yanıtsız görüşme yok.</Empty>
        ) : (
          <ul className="space-y-1.5">
            {silentApplications.slice(0, 8).map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onSelect?.(item.id)}
                  className="group flex w-full items-center gap-2 rounded-control border border-warn-border bg-warn-surface px-3 py-2 text-left transition hover:border-strong"
                >
                  <span className="min-w-0 flex-1">
                    <strong className="block truncate text-body text-primary">{item.title}</strong>
                    <span className="text-micro text-muted">{item.organization || "Kurum belirtilmemiş"}</span>
                  </span>
                  <Chip tone="warn">{item.days_silent} gün</Chip>
                  <ArrowRight size={13} className="shrink-0 text-muted transition group-hover:translate-x-0.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
