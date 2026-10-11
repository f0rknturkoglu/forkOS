import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import type { DayDetail, HeatmapDay } from "@/core/types";
import { Button } from "@/core/ui";
import { describe } from "@/core/verbs";
import { formatTrDate, formatTrDateTime } from "@/lib/date";

export function HeatmapPreview({ entry, labels }: { entry: HeatmapDay; labels: Record<string, string> }) {
  const detail = useQuery({
    queryKey: ["activity", "day", entry.day],
    queryFn: () => api.get<DayDetail>(`/activity/day${qs({ day: entry.day })}`),
    enabled: entry.total > 0,
    staleTime: 5 * 60_000,
  });
  const events = detail.data?.events.filter((event) => event.kind !== null) ?? [];
  return (
    <div className="stack-y-2 p-3 text-meta">
      <p className="font-medium text-primary">
        {formatTrDate(entry.day, { day: "numeric", month: "long", year: "numeric" })}
      </p>
      {entry.total === 0 ? (
        <p className="text-muted">Kayıt yok</p>
      ) : (
        <>
          <p className="text-secondary">
            {Object.entries(entry.kinds)
              .map(([kind, count]) => `${count} ${labels[kind] ?? kind}`)
              .join(" · ")}
          </p>
          {detail.isPending && (
            <p role="status" className="text-muted">
              Yükleniyor…
            </p>
          )}
          {detail.isError && (
            <div className="flex items-center gap-2 text-danger">
              <span>Ayrıntılar alınamadı.</span>
              <Button size="sm" variant="ghost" onClick={() => void detail.refetch()}>
                Yeniden dene
              </Button>
            </div>
          )}
          <ul className="max-h-44 overflow-y-auto stack-y-2">
            {events.slice(0, 5).map((event) => (
              <li key={event.id} className="flex items-baseline gap-2">
                <time className="shrink-0 tabular-nums text-muted">
                  {formatTrDateTime(event.occurred_at, { hour: "2-digit", minute: "2-digit" })}
                </time>
                <span className="min-w-0 break-words text-secondary">{describe(event.verb, event.payload)}</span>
              </li>
            ))}
          </ul>
          {events.length > 5 && <p className="text-muted">+{events.length - 5} hareket</p>}
        </>
      )}
      <a href={`#/day?d=${entry.day}`} className="inline-flex text-accent">
        Günü aç →
      </a>
    </div>
  );
}
