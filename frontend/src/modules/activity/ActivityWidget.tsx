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
          className="text-xs text-neutral-500 hover:text-neutral-300"
        >
          tumu -&gt;
        </button>
      }
    >
      {data.length === 0 ? (
        <Empty>Henuz hareket yok.</Empty>
      ) : (
        <ul className="space-y-1">
          {data.map((event) => (
            <li
              key={event.id}
              className={cx(
                "truncate text-xs",
                ALERT_VERBS.has(event.verb) ? "text-amber-400" : "text-neutral-400",
              )}
            >
              {describe(event.verb, event.payload)}
              <span className="ml-1 text-neutral-600">{relativeTime(event.occurred_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
