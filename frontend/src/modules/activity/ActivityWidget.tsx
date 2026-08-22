import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Empty, Section, cx, relativeTime } from "@/core/ui";
import { navigate } from "@/app/router";
import type { ActivityEvent } from "@/core/types";
import { ALERT_VERBS, describe } from "./verbs";

/**
 * Panelin en alt kosesindeki kucuk gunluk.
 * Bilincli olarak dar: burasi bir kayit akisi, calisma yuzeyi degil --
 * detay icin /activity var. Bes satir, ayirac yok, tek satirlik ozet.
 */
export function ActivityWidget() {
  const { data = [] } = useQuery({
    queryKey: ["activity", "widget"],
    queryFn: () => api.get<ActivityEvent[]>(`/activity${qs({ limit: 5 })}`),
  });

  return (
    <Section
      title="Son hareketler"
      action={
        <button
          onClick={() => navigate("/activity")}
          className="text-meta text-muted hover:text-primary"
        >
          tümü →
        </button>
      }
    >
      {data.length === 0 ? (
        <Empty>Henüz hareket yok.</Empty>
      ) : (
        <ul className="space-y-1">
          {data.slice(0, 5).map((event) => (
            <li
              key={event.id}
              className={cx(
                "flex items-baseline gap-2 text-[11px] leading-5",
                ALERT_VERBS.has(event.verb) ? "text-warn" : "text-muted",
              )}
            >
              <span className="min-w-0 flex-1 truncate">
                {describe(event.verb, event.payload)}
              </span>
              <span className="shrink-0 tabular-nums">{relativeTime(event.occurred_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}
