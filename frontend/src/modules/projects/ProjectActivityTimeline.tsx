import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays } from "lucide-react";
import { api, qs } from "@/core/api";
import type { ProjectEvent, ProjectJournalDay } from "@/core/types";
import { Empty, Field, Input, Section, SectionHeader, Skeleton, cx, relativeTime } from "@/core/ui";
import { VERB_LABELS } from "@/core/verbs";
import { keyToUtc, todayKey } from "@/lib/date";

/**
 * Gunluge gore gruplanmis proje hareketleri (salt okunur).
 *
 * Gunluk NOTU artik forkOS'ta yasamaz; bu yuzey yalnizca projenin operasyonel
 * izini gosterir. Yazma yuzeyi `ProjectJournalBridge` uzerinden Obsidian'dir.
 * Yanit sozlesmesi `note` alanini TASIMAZ; gunluk metni Vault'a aittir.
 */
type JournalDayGroup = ProjectJournalDay;

function eventTone(verb: string): string {
  if (verb.startsWith("github.")) return "bg-feed-gh";
  if (verb.startsWith("todo.")) return "bg-accent";
  if (verb.startsWith("note.")) return "bg-warn";
  if (verb.startsWith("project.")) return "bg-ok";
  return "bg-strong";
}

function dayLabel(day: string): string {
  return keyToUtc(day).toLocaleDateString("tr-TR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

function eventText(event: ProjectEvent): string | null {
  return (
    event.title ?? (event.payload.message as string | undefined) ?? (event.payload.title as string | undefined) ?? null
  );
}

/** Vault'a tasinan eski `note.*` olaylari artik proje hareketi degildir. */
function visibleProjectEvents(events: ProjectEvent[]): ProjectEvent[] {
  return events.filter((event) => !event.verb.startsWith("note."));
}

function projectEventLabel(verb: string): string {
  return VERB_LABELS[verb] ?? "Proje hareketi";
}

function EventRows({ events }: { events: ProjectEvent[] }) {
  return (
    <ul className="stack-divide-y divide-subtle">
      {events.map((event) => {
        const text = eventText(event);
        return (
          <li key={event.id} className="flex min-w-0 items-start gap-2 py-2 text-body">
            <span className={cx("mt-1.5 h-2 w-2 shrink-0 rounded-full", eventTone(event.verb))} aria-hidden />
            <div className="min-w-0 flex-1 sm:flex sm:items-baseline sm:gap-2">
              <span className="block shrink-0 text-secondary">{projectEventLabel(event.verb)}</span>
              {text && <span className="block min-w-0 truncate text-primary">{text}</span>}
            </div>
            <span className="shrink-0 text-meta text-muted">{relativeTime(event.occurred_at)}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function ProjectActivityTimeline({ projectId }: { projectId: string }) {
  const today = todayKey();
  const [selectedDay, setSelectedDay] = useState(today);

  const journalQuery = useQuery({
    queryKey: ["project-journal", projectId],
    queryFn: () => api.get<JournalDayGroup[]>(`/projects/${projectId}/journal${qs({ limit: 60 })}`),
  });
  const groups = journalQuery.data ?? [];
  const activeGroup = groups.find((group) => group.day === selectedDay);
  const activeEvents = visibleProjectEvents(activeGroup?.events ?? []);
  const historyGroups = groups.filter((group) => group.day !== selectedDay);

  useEffect(() => {
    setSelectedDay(today);
  }, [projectId, today]);

  return (
    <Section title="Proje hareketleri" hint="güne göre proje olayları" bodyClassName="stack-y-4">
      <article
        data-testid="project-journal-active-day"
        className="overflow-hidden rounded-control border border-accent bg-accent-surface"
      >
        <header className="flex flex-wrap items-end gap-3 border-b border-accent px-3 py-3">
          <Field label="Gün" className="w-full sm:w-48">
            <Input
              type="date"
              value={selectedDay}
              max={today}
              onChange={(value) => {
                if (value && value <= today) setSelectedDay(value);
              }}
              ariaLabel="Gün"
              className="w-full bg-surface"
            />
          </Field>
          <div className="min-w-0 flex-1 pb-1">
            <p className="text-meta text-muted">Seçili gün</p>
            <h3 className="truncate text-body font-medium text-primary">{dayLabel(selectedDay)}</h3>
          </div>
          <span className="pb-1 text-meta text-muted">{activeEvents.length} hareket</span>
        </header>

        <div className="border-t border-subtle bg-surface px-3 py-2">
          <SectionHeader label="Günün hareketleri" hint={`${activeEvents.length}`} />
          {journalQuery.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : journalQuery.isError ? (
            <p className="py-2 text-meta text-danger">Proje hareketleri alınamadı.</p>
          ) : activeEvents.length === 0 ? (
            <p className="py-2 text-meta text-muted">Bu gün henüz proje hareketi yok.</p>
          ) : (
            <EventRows events={activeEvents} />
          )}
        </div>
      </article>

      {journalQuery.isError ? (
        <Empty>Proje günlüğü alınamadı.</Empty>
      ) : historyGroups.length > 0 ? (
        <div>
          <SectionHeader label="Geçmiş günler" hint={`${historyGroups.length}`} />
          <div className="stack-y-3">
            {historyGroups.map((group) => {
              const events = visibleProjectEvents(group.events);
              return (
                <article
                  key={group.day}
                  data-project-journal-day={group.day}
                  className="rounded-control border border-subtle bg-surface px-3 py-2.5"
                >
                  <button
                    type="button"
                    onClick={() => setSelectedDay(group.day)}
                    className="flex w-full items-center gap-2 text-left"
                  >
                    <CalendarDays size={14} className="shrink-0 text-muted" />
                    <span className="text-body font-medium text-primary">{dayLabel(group.day)}</span>
                    <span className="ml-auto text-meta text-muted">{events.length} hareket</span>
                  </button>

                  {events.length > 0 && (
                    <div className="mt-2 border-t border-subtle">
                      <EventRows events={events} />
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        </div>
      ) : null}
    </Section>
  );
}
