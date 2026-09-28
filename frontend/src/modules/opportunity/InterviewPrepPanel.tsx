import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, CheckCircle2, Circle, Wallet } from "lucide-react";
import { api } from "@/core/api";
import { Button, Checkbox, Chip, Empty, Section, Spinner, cx } from "@/core/ui";
import type { CareerStory, Interview, InterviewPrepGroup, Opportunity, SalaryConsistency } from "@/core/types";
import { applicationStatusLabel } from "./labels";
import { InterviewIntelligencePanel } from "./InterviewIntelligencePanel";

interface PrepGroup {
  application: Opportunity;
  interviews: Interview[];
  salary: SalaryConsistency;
}

const CHECKLIST_KEY = "forkos:interview-prep";

type ChecklistState = Record<string, Record<string, true>>;

function readChecklist(): ChecklistState {
  try {
    const raw = window.localStorage.getItem(CHECKLIST_KEY);
    return raw ? (JSON.parse(raw) as ChecklistState) : {};
  } catch {
    return {};
  }
}

function isUpcoming(interview: Interview): boolean {
  if (!interview.scheduled_at) return true;
  return new Date(interview.scheduled_at).getTime() >= Date.now();
}

export function InterviewPrepPanel() {
  const [checks, setChecks] = useState<ChecklistState>(readChecklist);
  const {
    data: groups = [],
    isLoading,
    isError,
    error,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ["career-interview-prep"],
    // Kayıt başına iki istek yerine TEK toplu okuma (eskiden 2N istek vardı).
    queryFn: async (): Promise<PrepGroup[]> => {
      const groups = await api.get<InterviewPrepGroup[]>("/career/interview-prep");
      return groups.map((group) => ({
        application: group.opportunity,
        interviews: group.interviews,
        salary: group.salary,
      }));
    },
  });
  const { data: stories = [], isError: storiesFailed } = useQuery({
    queryKey: ["career-stories"],
    queryFn: () => api.get<CareerStory[]>("/career/stories"),
  });

  const upcoming = useMemo(
    () =>
      groups
        .map((group) => ({ ...group, interviews: group.interviews.filter(isUpcoming) }))
        .filter((group) => group.interviews.length > 0)
        .sort((left, right) => {
          const leftAt = left.interviews[0]?.scheduled_at ?? "";
          const rightAt = right.interviews[0]?.scheduled_at ?? "";
          return leftAt.localeCompare(rightAt);
        }),
    [groups],
  );

  function toggle(interviewId: string, itemId: string) {
    setChecks((current) => {
      const forInterview = { ...(current[interviewId] ?? {}) };
      if (forInterview[itemId]) delete forInterview[itemId];
      else forInterview[itemId] = true;
      const next = { ...current, [interviewId]: forInterview };
      try {
        window.localStorage.setItem(CHECKLIST_KEY, JSON.stringify(next));
      } catch {
        // Yerel depolama kapalıysa işaretler oturumla sınırlı kalır.
      }
      return next;
    });
  }

  if (isLoading) return <Spinner label="Mülakat hazırlığı yükleniyor…" />;
  if (isError) {
    return (
      <Section title="Mülakat hazırlığı" hint="okunamadı">
        <div role="alert" className="space-y-2 rounded-control border border-danger-border bg-danger-surface px-3 py-3">
          <p className="text-meta text-danger">
            Mülakat hazırlığı yüklenemedi: {error instanceof Error ? error.message : "bilinmeyen hata"}
          </p>
          <Button size="sm" disabled={isFetching} onClick={() => void refetch()}>
            Tekrar dene
          </Button>
        </div>
      </Section>
    );
  }
  if (upcoming.length === 0) {
    return (
      <Section title="Mülakat hazırlığı" hint="Yaklaşan görüşme yok">
        <Empty title="Planlanmış görüşme yok">
          Başvuru detayından görüşme tarihi eklediğinde hazırlık listesi burada belirir.
        </Empty>
      </Section>
    );
  }

  return (
    <Section title="Mülakat hazırlığı" hint={`${upcoming.length} başvuruda yaklaşan görüşme`}>
      <div className="space-y-4">
        {storiesFailed && (
          <p role="alert" className="text-meta text-danger">
            Hikâye bankası okunamadı: eşleşen hikâye adları gösterilemiyor.
          </p>
        )}
        {upcoming.map(({ application, interviews, salary }) => {
          const relevant = (application.evaluation?.matches ?? [])
            .filter((match) => match.story_ids.length > 0)
            .map((match) => ({
              requirement: match.requirement,
              stories: match.story_ids
                .map((id) => stories.find((story) => story.id === id))
                .filter((story): story is CareerStory => Boolean(story)),
            }));
          return (
            <div key={application.id} className="rounded-card border border-subtle bg-surface p-4">
              <div className="flex flex-wrap items-center gap-2">
                <CalendarClock size={15} className="text-icon" />
                <strong className="text-body text-primary">{application.title}</strong>
                {application.organization && (
                  <span className="text-meta text-secondary">{application.organization}</span>
                )}
                {application.application_status && (
                  <Chip tone="accent">{applicationStatusLabel(application.application_status)}</Chip>
                )}
              </div>

              {salary.inconsistent && (
                <p className="mt-2 flex items-center gap-2 rounded-control border border-warn-border bg-warn-surface p-2 text-meta text-secondary">
                  <Wallet size={14} className="text-warn" />
                  {salary.warning ?? "Ücret beyanları tutarsız."}
                </p>
              )}

              <div className="mt-3 space-y-3">
                {interviews.map((interview) => {
                  const items = [
                    { id: "notes", label: "Görüşme notlarını ve gündemi gözden geçir", done: Boolean(interview.notes) },
                    {
                      id: "salary",
                      label: "Ücret beklentisini netleştir",
                      done: salary.claims.length > 0 && !salary.inconsistent,
                    },
                    {
                      id: "stories",
                      label: "Bu kurumun gereksinimlerine uyan hikâyeleri seç",
                      done: relevant.length > 0,
                    },
                    { id: "questions", label: "Soracağın en az üç soruyu yaz", done: false },
                    {
                      id: "logistics",
                      label: "Görüşme biçimini ve bağlantı bilgisini doğrula",
                      done: Boolean(interview.mode),
                    },
                  ];
                  const checked = checks[interview.id] ?? {};
                  return (
                    <div key={interview.id} className="rounded-control border border-subtle bg-surface-sunken p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-meta text-primary">
                          {interview.stage}
                          {interview.mode ? ` · ${interview.mode}` : ""}
                        </span>
                        <span className="text-meta text-muted">
                          {interview.scheduled_at
                            ? new Date(interview.scheduled_at).toLocaleString("tr-TR")
                            : "Tarih belirtilmedi"}
                        </span>
                      </div>
                      <div className="mt-2 space-y-1">
                        {items.map((item) => (
                          <div key={item.id} className="flex items-center gap-2">
                            <Checkbox
                              checked={Boolean(checked[item.id])}
                              onChange={() => toggle(interview.id, item.id)}
                              label={item.label}
                            />
                            {item.done ? (
                              <CheckCircle2 size={13} className="text-ok" aria-label="Veri hazır" />
                            ) : (
                              <Circle size={13} className="text-icon" aria-label="Veri eksik" />
                            )}
                          </div>
                        ))}
                      </div>
                      <InterviewIntelligencePanel interviewId={interview.id} />
                    </div>
                  );
                })}
              </div>

              {relevant.length > 0 && (
                <div className="mt-3">
                  <span className="text-meta font-medium text-secondary">
                    Bu kurumun gereksinimlerine en yakın hikâyeler
                  </span>
                  <ul className="mt-1 space-y-1">
                    {relevant.map((entry) => (
                      <li
                        key={entry.requirement}
                        className="flex flex-wrap items-center gap-1 text-meta text-secondary"
                      >
                        <span className="text-primary">{entry.requirement}</span>
                        <span className="text-muted">→</span>
                        {entry.stories.map((story) => (
                          <Chip key={story.id} tone="accent">
                            {story.title}
                          </Chip>
                        ))}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {salary.claims.length > 0 && (
                <div className="mt-3">
                  <span className={cx("text-meta font-medium", salary.inconsistent ? "text-warn" : "text-secondary")}>
                    Ücret beyanları
                  </span>
                  <ul className="mt-1 space-y-1">
                    {salary.claims.map((claim) => (
                      <li key={`${claim.interview_id}-${claim.stage}`} className="text-meta text-secondary">
                        <span className="text-muted">{claim.stage}:</span> {claim.statement}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Section>
  );
}
