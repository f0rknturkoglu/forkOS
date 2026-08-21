import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Empty, Panel, cx, relativeTime } from "@/core/ui";
import { navigate } from "@/app/router";
import type { ActivityEvent } from "@/core/types";
import { ALERT_VERBS, describe } from "./verbs";

export function ActivityWidget() {
  const { data = [] } = useQuery({
    queryKey: ["activity", "widget"],
    queryFn: () => api.get<ActivityEvent[]>(`/activity${qs({ limit: 10 })}`),
  });

  return (
    <Panel
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
          {data.map((event) => (
            <li
              key={event.id}
              className={cx(
                "truncate text-meta",
                ALERT_VERBS.has(event.verb) ? "text-warn" : "text-secondary",
              )}
            >
              {describe(event.verb, event.payload)}
              <span className="ml-1 text-muted">{relativeTime(event.occurred_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
