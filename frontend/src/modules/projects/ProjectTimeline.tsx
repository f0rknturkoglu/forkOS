import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Badge, Empty, Section, cx, relativeTime } from "@/core/ui";
import type { ProjectEvent } from "@/core/types";
import { VERB_LABELS } from "@/modules/activity/verbs";

/** Commit ve gorev olaylarini ayirt eden nokta rengi. */
function toneOf(verb: string): string {
  if (verb.startsWith("github.")) return "bg-feed-gh";
  if (verb.startsWith("todo.")) return "bg-accent";
  if (verb.startsWith("project.")) return "bg-ok";
  return "bg-strong";
}

/**
 * Projenin gunlugu.
 *
 * Kaynak `event` tablosu -- append-only oldugu icin burasi gecmisin tam ve
 * degistirilemez kaydi. Ayri bir "proje notu" defterine gerek yok: ne
 * yaptigin zaten yaparken yazildi.
 */
export function ProjectTimeline({ projectId }: { projectId: string }) {
  const { data = [], isLoading } = useQuery({
    queryKey: ["project-timeline", projectId],
    queryFn: () => api.get<ProjectEvent[]>(`/projects/${projectId}/timeline${qs({ limit: 60 })}`),
  });

  return (
    <Section title="Günlük" hint={data.length > 0 ? `son ${data.length} kayıt` : undefined}>
      {isLoading ? (
        <p className="py-2 text-meta text-muted">Yükleniyor…</p>
      ) : data.length === 0 ? (
        <Empty>Henüz kayıt yok. Görev ekleyip tamamladıkça burada birikir.</Empty>
      ) : (
        <ul className="relative ml-1 border-l border-strong">
          {data.map((event) => {
            const message = (event.payload.message as string | undefined)
              ?? (event.payload.title as string | undefined);
            const url = event.payload.url as string | undefined;
            return (
              <li key={event.id} className="relative min-h-9 py-1.5 pl-5">
                <span className="absolute -left-[5px] top-3" aria-hidden>
                  <span className={cx("block h-2.5 w-2.5 rounded-full ring-[3px] ring-surface",
                    toneOf(event.verb))} />
                </span>
                <div className="flex min-w-0 flex-wrap items-baseline gap-x-2 text-body">
                  <span className="numeral shrink-0 text-meta tabular-nums text-muted">
                    {new Date(event.occurred_at).toLocaleDateString("tr-TR", {
                      day: "numeric", month: "short",
                    })}
                  </span>
                  <span className="text-secondary">{VERB_LABELS[event.verb] ?? event.verb}</span>
                  {(event.title || message) && (
                    url ? (
                      <a href={url} target="_blank" rel="noreferrer"
                        className="min-w-0 truncate text-primary hover:text-accent">
                        {event.title ?? message}
                      </a>
                    ) : (
                      <span className="min-w-0 truncate text-primary">{event.title ?? message}</span>
                    )
                  )}
                  {event.entity_type && <Badge>{event.entity_type}</Badge>}
                  <span className="text-meta text-muted">{relativeTime(event.occurred_at)}</span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Section>
  );
}
