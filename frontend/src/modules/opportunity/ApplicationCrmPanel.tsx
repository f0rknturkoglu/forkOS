import { useQuery } from "@tanstack/react-query";
import { BarChart3, CalendarClock } from "lucide-react";
import { api } from "@/core/api";
import {Chip, Empty, Section, cx, relativeTime} from "@/core/ui";
import { navigate } from "@/app/router";
import type { ApplicationFunnel, Followup } from "@/core/types";
import { STATUS_TONES, statusLabel } from "./labels";

/** Basvuru CRM ozeti: funnel, donusum oranlari, red nedenleri, yaklasan takipler. */
export function ApplicationCrmPanel() {
  const { data: funnel } = useQuery({
    queryKey: ["applications-funnel"],
    queryFn: () => api.get<ApplicationFunnel>("/applications/funnel"),
    refetchInterval: 60_000,
  });
  const { data: followups = [] } = useQuery({
    queryKey: ["followups"],
    queryFn: () => api.get<Followup[]>("/opportunities/followups"),
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
                <div key={row.status} className="flex items-center gap-3">
                  <span className="w-28 shrink-0 truncate text-meta text-secondary">{statusLabel(row.status)}</span>
                  <div className="h-4 min-w-0 flex-1 overflow-hidden rounded-control bg-surface-sunken">
                    <div
                      className={cx("h-full rounded-control",
                        tone === "ok" ? "bg-ok" : tone === "danger" ? "bg-danger" : tone === "warn" ? "bg-warn" : "bg-accent",
                      )}
                      style={{ width: (row.count / maxCount) * 100 + "%" }}
                    />
                  </div>
                  <span className="numeral w-10 shrink-0 text-right text-meta text-primary">{row.count}</span>
                </div>
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
            {[["applied_to_interview", "Başvuru → Görüşme"],
              ["interview_to_offer", "Görüşme → Teklif"],
              ["offer_to_accepted", "Teklif → Kabul"],
              ["applied_to_rejected", "Başvuru → Red"]].map(([key, label]) => (
              <div key={key} className="rounded-control border border-subtle px-3 py-2">
                <div className="numeral text-title leading-tight text-primary">
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
          <ul className="space-y-1">
            {followups.slice(0, 8).map((f) => (
              <li key={f.id}>
                <button
                  type="button"
                  onClick={() => navigate("/opportunities")}
                  className="flex w-full items-center gap-2 rounded px-1.5 py-1 text-left transition hover:bg-surface-hover"
                >
                  <BarChart3 size={13} className="shrink-0 text-icon" />
                  <span className="min-w-0 flex-1 truncate text-body text-primary">{f.title}</span>
                  <Chip tone="warn">{relativeTime(f.follow_up_at)}</Chip>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}