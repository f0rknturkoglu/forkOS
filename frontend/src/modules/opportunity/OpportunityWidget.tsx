import { useQuery } from "@tanstack/react-query";
import { CalendarClock } from "lucide-react";
import { api } from "@/core/api";
import { RowList, Section } from "@/core/ui";
import type { Deadline, Followup, Notification } from "@/core/types";

export function DeadlineWidget() {
  const { data = [] } = useQuery({
    queryKey: ["deadlines"],
    queryFn: () => api.get<Deadline[]>("/deadlines"),
  });
  return (
    <Section title="Yaklaşan son tarihler">
      {data.length === 0 ? (
        <p className="text-meta text-muted">Yaklaşan son tarih yok.</p>
      ) : (
        <RowList>
          {data.slice(0, 5).map((x) => (
            <a
              key={x.entity_id}
              href={x.module === "opportunity" ? "#/opportunities" : "#/todos"}
              className="flex justify-between gap-3 py-2 text-meta hover:text-accent"
            >
              <span className="truncate">{x.title}</span>
              <span className="shrink-0 text-warn">{new Date(x.due_at).toLocaleDateString("tr-TR")}</span>
            </a>
          ))}
        </RowList>
      )}
    </Section>
  );
}

export function NotificationWidget() {
  const { data = [] } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.get<Notification[]>("/notifications"),
  });
  return (
    <Section title="Bildirimler" hint={`${data.filter((x) => !x.read_at).length} okunmamış`}>
      {data.length === 0 ? (
        <p className="text-meta text-muted">Yeni bildirim yok.</p>
      ) : (
        <RowList>
          {data.slice(0, 4).map((x) => (
            <div key={x.id} className="py-2 text-meta">
              <p className="text-secondary">{x.title}</p>
              {x.body && <p className="mt-0.5 line-clamp-2 text-muted">{x.body}</p>}
            </div>
          ))}
        </RowList>
      )}
    </Section>
  );
}

export function FollowupWidget() {
  const { data = [] } = useQuery({
    queryKey: ["followups"],
    queryFn: () => api.get<Followup[]>("/opportunities/followups"),
  });
  return (
    <Section title="Yaklaşan takipler" hint={<CalendarClock size={13} />}>
      {data.length === 0 ? (
        <p className="text-meta text-muted">Takipli başvuru yok.</p>
      ) : (
        <RowList>
          {data.slice(0, 5).map((x) => (
            <a
              key={x.id}
              href="#/opportunities"
              className="flex justify-between gap-3 py-2 text-meta hover:text-accent"
            >
              <span className="truncate">{x.title}</span>
              <span className="shrink-0 text-warn">{new Date(x.follow_up_at).toLocaleDateString("tr-TR")}</span>
            </a>
          ))}
        </RowList>
      )}
    </Section>
  );
}
