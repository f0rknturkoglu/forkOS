/**
 * Tekrar kuyrugu (Faz 10).
 *
 * Kaynak: `GET /study/review?window=14` — backend SRS alanlarindan
 * (next_review_at / mastery / review_count) beslenen bes bolum:
 * bugun, gecikenler, yaklasanlar, yeni ogrenilenler, zayif konular.
 *
 * Satir iki isi ayirir:
 *   - basligi tiklamak konuyu acar (derin baglanti; LF1 `?focus=` yazar),
 *   - hizli eylemler (derece verme / pomodoro) satirda kalir.
 * Derece, tekrar motorunun SOZLESMESIDIR: `forgot..very_easy` araligi
 * backend `GRADES` ile ayni olmali (app/modules/learning/review.py).
 */
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Timer } from "lucide-react";
import type { components } from "@/generated/api-schema";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Empty, RowList, SectionHeader, SkeletonRows, cx } from "@/core/ui";
import { openPomodoro } from "@/modules/pomodoro/dock";
import { useOnline } from "@/lib/hooks";
import { listDecks } from "@/modules/flashcard/api";
import { navigate } from "@/app/router";

type ReviewTopic = components["schemas"]["ReviewTopicOut"];
type ReviewQueue = components["schemas"]["ReviewQueueOut"];

/** Kuyruk penceresi (gun). Yaklasanlar bolumu bu araligi gosterir. */
const REVIEW_WINDOW_DAYS = 14;

const MS_PER_DAY = 86_400_000;

/** Backend `review.GRADES` sirasi korunur: kotuden iyiye. */
const GRADES = [
  { id: "forgot", label: "Unuttum", variant: "danger" },
  { id: "hard", label: "Zor", variant: "warn" },
  { id: "medium", label: "Orta", variant: "secondary" },
  { id: "easy", label: "Kolay", variant: "ok" },
  { id: "very_easy", label: "Çok kolay", variant: "ok" },
] as const;

/** Bolum sirasi ve basliklari tek yerde: hem cizim hem bos durum buradan. */
const SECTIONS: { key: keyof ReviewQueue; label: string; hint: string }[] = [
  { key: "due_today", label: "Bugün tekrar edilecekler", hint: "Tekrar zamanı bugün gelenler" },
  { key: "overdue", label: "Gecikenler", hint: "Planlanan tarihi geçen tekrarlar" },
  { key: "upcoming", label: "Yaklaşanlar", hint: `${REVIEW_WINDOW_DAYS} gün içinde` },
  { key: "new_topics", label: "Yeni öğrenilenler", hint: "Henüz tekrar edilmemiş konular" },
  { key: "weak", label: "Zayıf konular", hint: "Ustalığı düşük ya da sık unutulan" },
];

const startOfDay = (value: Date): number => new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime();

/** Sonraki tekrar tarihini "gecikti/bugün/tarih" olarak okunur hale getirir. */
function dueLabel(topic: ReviewTopic, now: Date): { text: string; tone: "danger" | "accent" | "muted" } {
  if (!topic.next_review_at) return { text: "Tekrar planlanmadı", tone: "muted" };
  const next = new Date(topic.next_review_at);
  const days = Math.round((startOfDay(next) - startOfDay(now)) / MS_PER_DAY);
  if (days < 0) return { text: `${-days} gün gecikti`, tone: "danger" };
  if (days === 0) return { text: "Bugün", tone: "accent" };
  if (days === 1) return { text: "Yarın", tone: "muted" };
  return { text: `${days} gün sonra`, tone: "muted" };
}

const dateText = (iso: string): string => new Date(iso).toLocaleDateString("tr-TR");

export function ReviewView({ onOpenTopic }: { onOpenTopic: (topicId: string) => void }) {
  return (
    <div className="stack-y-5">
      <DailyCardReviews />
      <TopicReviewView onOpenTopic={onOpenTopic} />
    </div>
  );
}

function DailyCardReviews() {
  const decks = useQuery({ queryKey: ["flashcard", "decks"], queryFn: () => listDecks() });
  const data = Array.isArray(decks.data) ? decks.data : [];
  const due = data.reduce((count, deck) => count + deck.due_count, 0);
  const fresh = data.reduce((count, deck) => count + deck.new_count, 0);
  return (
    <section aria-label="Kart tekrarları" className="stack-y-2 rounded-card border border-subtle p-3">
      <SectionHeader
        label="Kart tekrarları"
        hint={
          decks.isError ? "Yüklenemedi" : decks.isLoading ? "Yükleniyor…" : `${due} kart bekliyor · ${fresh} yeni kart`
        }
      />
      {decks.isError ? (
        <p role="alert" className="text-meta text-danger">
          Kartlar yüklenemedi.{" "}
          <Button size="sm" onClick={() => void decks.refetch()}>
            Kartları yeniden dene
          </Button>
        </p>
      ) : (
        !decks.isLoading && (
          <>
            {!due && !fresh && <p className="text-meta text-muted">Bugün bekleyen kart yok.</p>}
            <div className="flex flex-wrap gap-2">
              {data
                .filter((deck) => deck.due_count + deck.new_count > 0)
                .map((deck) => (
                  <Button
                    key={deck.id}
                    size="sm"
                    onClick={() => navigate(`/flashcard?deck=${deck.id}&review=due&return=learning-review`)}
                  >
                    {deck.title} · {deck.due_count} bekleyen{deck.new_count ? ` · ${deck.new_count} yeni` : ""}
                  </Button>
                ))}
            </div>
            {due + fresh > 0 && (
              <Button size="sm" onClick={() => navigate("/flashcard?review=due&return=learning-review")}>
                Kart tekrarını başlat
              </Button>
            )}
          </>
        )
      )}
      <p className="text-meta text-muted">Konu tekrarları aşağıda; kartlar ve konular ayrı kuyruklardır.</p>
    </section>
  );
}

function TopicReviewView({ onOpenTopic }: { onOpenTopic: (topicId: string) => void }) {
  const online = useOnline();
  const [gradingId, setGradingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const queue = useQuery({
    queryKey: ["study-review", REVIEW_WINDOW_DAYS],
    queryFn: () => api.get<ReviewQueue>(`/study/review?window=${REVIEW_WINDOW_DAYS}&limit=50`),
  });

  const grade = useMutation({
    mutationFn: (payload: { id: string; grade: string }) =>
      api.post(`/study/topics/${payload.id}/review`, { grade: payload.grade }),
    onSuccess: () => {
      setGradingId(null);
      invalidateAfter("study.write");
    },
    onError: (cause: Error) => setError(cause.message),
  });

  if (queue.isLoading) {
    return (
      <div className="stack-y-3">
        <p role="status" className="text-meta text-muted">
          Tekrar kuyruğu yükleniyor…
        </p>
        <SkeletonRows rows={4} />
      </div>
    );
  }

  if (queue.isError) {
    return (
      <div role="alert">
        <Empty
          variant="page"
          title="Tekrar kuyruğu yüklenemedi"
          action={
            <Button disabled={queue.isFetching} onClick={() => void queue.refetch()}>
              Yeniden dene
            </Button>
          }
        >
          Sunucudan yanıt alamadım: {queue.error.message}
        </Empty>
      </div>
    );
  }

  const data = queue.data ?? {};
  const total = SECTIONS.reduce((sum, section) => sum + (data[section.key] ?? []).length, 0);
  const now = new Date();
  const upcoming = data.upcoming ?? [];
  const nearest = upcoming
    .map((topic) => topic.next_review_at)
    .filter((iso): iso is string => Boolean(iso))
    .sort()[0];

  if (total === 0) {
    return (
      <Empty variant="page" title="Bugün tekrar edilecek konu yok">
        Tekrar kuyruğu boş. Bir konuyu çalışıp tekrar verdiğinde ya da yeni konu eklediğinde burada görünür.
      </Empty>
    );
  }

  return (
    <div className="stack-y-5">
      {error && (
        <p role="alert" className="text-meta text-danger">
          {error}
        </p>
      )}

      {SECTIONS.map((section) => {
        const topics = data[section.key] ?? [];
        if (topics.length === 0 && section.key !== "due_today") return null;
        return (
          <section key={section.key}>
            <SectionHeader label={section.label} hint={`${topics.length} konu · ${section.hint}`} />
            {topics.length === 0 ? (
              <Empty>
                Bugün tekrar edilecek konu yok.
                {nearest && ` En yakın tekrar: ${dateText(nearest)}.`}
              </Empty>
            ) : (
              <RowList as="ul">
                {topics.map((topic) => {
                  const due = dueLabel(topic, now);
                  const grading = gradingId === topic.id;
                  return (
                    <li key={topic.id} className="py-2.5">
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
                        <button
                          type="button"
                          onClick={() => onOpenTopic(topic.id)}
                          className="min-w-0 flex-1 text-left"
                        >
                          <span className="block whitespace-normal break-words text-body text-primary">
                            {topic.title}
                          </span>
                          <span className="block truncate text-meta text-muted">{topic.area_title}</span>
                        </button>
                        <span
                          className={cx(
                            "shrink-0 text-meta",
                            due.tone === "danger"
                              ? "text-danger"
                              : due.tone === "accent"
                                ? "text-accent"
                                : "text-muted",
                          )}
                        >
                          {due.text}
                          {topic.next_review_at && ` · ${dateText(topic.next_review_at)}`}
                        </span>
                        <MasteryBar title={topic.title} mastery={topic.mastery ?? null} />
                        <div className="flex shrink-0 items-center gap-1.5">
                          <Button
                            size="sm"
                            disabled={!online}
                            ariaExpanded={grading}
                            onClick={() => setGradingId(grading ? null : topic.id)}
                          >
                            Tekrar yap
                          </Button>
                          <Button size="sm" onClick={() => openPomodoro({ context: topic.id, topic: topic.title })}>
                            <Timer size={13} /> Pomodoro
                          </Button>
                        </div>
                      </div>

                      {grading && (
                        <div className="mt-2 flex flex-wrap items-center gap-1.5 rounded-card border border-subtle bg-surface-sunken p-2">
                          <span className="mr-1 text-meta text-secondary">Ne kadar hatırladın?</span>
                          {GRADES.map((option) => (
                            <Button
                              key={option.id}
                              size="sm"
                              variant={option.variant}
                              disabled={!online || grade.isPending}
                              onClick={() => grade.mutate({ id: topic.id, grade: option.id })}
                            >
                              {option.label}
                            </Button>
                          ))}
                          <span className="text-meta text-muted">Derece, sonraki tekrar tarihini belirler.</span>
                        </div>
                      )}
                    </li>
                  );
                })}
              </RowList>
            )}
          </section>
        );
      })}
    </div>
  );
}

/** Ustalik cubugu; sayi her zaman metin olarak da gorunur (renk tek basina anlatmaz). */
function MasteryBar({ title, mastery }: { title: string; mastery: number | null }) {
  if (mastery === null) {
    return <span className="shrink-0 text-meta text-muted">Ustalık —</span>;
  }
  return (
    <span className="flex shrink-0 items-center gap-1.5">
      <span
        role="progressbar"
        aria-label={`Ustalık: ${title}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={mastery}
        className="block h-1.5 w-16 overflow-hidden rounded-control bg-surface-sunken"
      >
        <span className="block h-full bg-accent" style={{ width: `${mastery}%` }} />
      </span>
      <span className="numeral text-meta text-secondary">%{mastery}</span>
    </span>
  );
}
