import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CalendarDays } from "lucide-react";
import { api, qs } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import type { ProjectEvent, ProjectJournalDay } from "@/core/types";
import { Chip, Empty, Field, Input, Section, Textarea, cx, relativeTime, useToast } from "@/core/ui";
import { VERB_LABELS } from "@/core/verbs";
import { keyToUtc, todayKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";

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

export function ProjectJournal({ projectId }: { projectId: string }) {
  const today = todayKey();
  const online = useOnline();
  const toast = useToast();
  const [selectedDay, setSelectedDay] = useState(today);

  const journalQuery = useQuery({
    queryKey: ["project-journal", projectId],
    queryFn: () => api.get<ProjectJournalDay[]>(`/projects/${projectId}/journal${qs({ limit: 60 })}`),
  });
  const groups = journalQuery.data ?? [];
  const selected = groups.find((group) => group.day === selectedDay);
  const savedBody = selected?.note?.body ?? "";
  const [draft, setDraft] = useState(savedBody);

  useEffect(() => {
    setSelectedDay(today);
  }, [projectId, today]);
  useEffect(() => {
    setDraft(savedBody);
  }, [selectedDay, savedBody]);

  const save = useMutation({
    mutationFn: (body: string) => api.put(`/projects/${projectId}/journal/${selectedDay}`, { body }),
    onSuccess: () => invalidateAfter("note.write", "project.write", "link.write"),
    onError: () => toast.push("Günlük notu kaydedilemedi.", { tone: "danger" }),
  });

  return (
    <Section title="Günlük" hint="günlük notlar ve proje hareketleri" bodyClassName="space-y-4">
      <div className="grid gap-3 border-b border-subtle pb-4 sm:grid-cols-[180px_minmax(0,1fr)]">
        <Field label="Gün">
          <Input
            type="date"
            value={selectedDay}
            max={today}
            onChange={(value) => {
              if (value && value <= today) setSelectedDay(value);
            }}
            ariaLabel="Gün"
            className="w-full"
          />
        </Field>
        <Field
          label={dayLabel(selectedDay)}
          hint={
            !online
              ? "Çevrimdışıyken günlük okunabilir; yazma kapalıdır."
              : draft.trim() !== savedBody.trim()
                ? "Kaydedilmedi; alandan çıkınca kaydedilir."
                : "Her proje için günde tek düzenlenebilir not."
          }
        >
          <Textarea
            value={draft}
            onChange={setDraft}
            onBlur={(value) => {
              const normalized = value.trim();
              if (normalized !== savedBody.trim()) save.mutate(normalized);
            }}
            disabled={!online || save.isPending}
            rows={6}
            ariaLabel="Günlük notu"
            placeholder="Bugün ne oldu, hangi karar alındı, sıradaki bağlam ne?"
            className="font-mono text-meta leading-6"
          />
        </Field>
      </div>

      {journalQuery.isLoading ? (
        <p className="py-2 text-meta text-muted">Yükleniyor…</p>
      ) : journalQuery.isError ? (
        <Empty>Proje günlüğü alınamadı.</Empty>
      ) : groups.length === 0 ? (
        <Empty>Henüz günlük kaydı yok. Bugünün notunu yazabilir veya projede bir hareket yapabilirsin.</Empty>
      ) : (
        <div className="space-y-3">
          {groups.map((group) => {
            const active = group.day === selectedDay;
            return (
              <article
                key={group.day}
                data-project-journal-day={group.day}
                className={cx(
                  "rounded-control border px-3 py-2.5",
                  active ? "border-accent bg-accent-surface" : "border-subtle bg-surface",
                )}
              >
                <button
                  type="button"
                  onClick={() => setSelectedDay(group.day)}
                  aria-current={active ? "date" : undefined}
                  className="flex w-full items-center gap-2 text-left"
                >
                  <CalendarDays size={14} className={active ? "text-accent" : "text-muted"} />
                  <span className="text-body font-medium text-primary">{dayLabel(group.day)}</span>
                  <span className="ml-auto text-meta text-muted">{group.events.length} hareket</span>
                </button>

                {group.note && (
                  <p className="mt-2 whitespace-pre-wrap border-l-2 border-warn-border pl-3 text-body text-secondary">
                    {group.note.body}
                  </p>
                )}

                {group.events.length > 0 && (
                  <ul className="mt-2 divide-y divide-subtle border-t border-subtle">
                    {group.events.map((event) => {
                      const text = eventText(event);
                      return (
                        <li key={event.id} className="flex min-w-0 items-baseline gap-2 py-2 text-body">
                          <span className={cx("h-2 w-2 shrink-0 rounded-full", eventTone(event.verb))} aria-hidden />
                          <span className="shrink-0 text-secondary">{VERB_LABELS[event.verb] ?? event.verb}</span>
                          {text && <span className="min-w-0 truncate text-primary">{text}</span>}
                          {event.entity_type && <Chip>{event.entity_type}</Chip>}
                          <span className="ml-auto shrink-0 text-meta text-muted">
                            {relativeTime(event.occurred_at)}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </article>
            );
          })}
        </div>
      )}
    </Section>
  );
}
