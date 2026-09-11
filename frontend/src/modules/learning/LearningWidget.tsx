/**
 * Ogrenme widget'i (Faz 12: study + learning birlesik).
 *
 * Tek liste, IKI farkli kayit tipi: devam eden kurslar ve tekrar bekleyen
 * konular. Satirlar hem ikon hem ETIKETLE ayrilir ("Kurs"/"Konu") ve her tip
 * kendi derin baglantisina gider:
 *   - konu  -> `#/learning?focus=<id>`      (konu ayrintisi)
 *   - kurs  -> `#/learning?view=courses&course=<id>`
 * Hepsini `#/learning`'a gondermek kullaniciyi bos sayfada birakiyordu.
 */
import { useQuery } from "@tanstack/react-query";
import { BookOpen, Brain } from "lucide-react";
import type { components } from "@/generated/api-schema";
import { api, qs } from "@/core/api";
import { Empty, RowList, Section } from "@/core/ui";

type Course = components["schemas"]["CourseOut"];
type StudyTopic = components["schemas"]["StudyTopicOut"];
type StalePage = components["schemas"]["StalePageOut"];

/** Kac gun dokunulmayan konu "bayat" sayilir. TEK yerde durur: kullanici
 *  tercihi yoksa backend varsayilaniyla (app/modules/learning/service.py
 *  DEFAULT_STALE_DAYS) ayni deger kabul edilir. */
const STALE_DAYS = 21;

/** Widget'ta gosterilen satir sayisi (liste uzarsa Today paneli bozulur). */
const ROWS_PER_KIND = 3;

const MS_PER_DAY = 86_400_000;

export function LearningWidget() {
  const courses = useQuery({
    queryKey: ["courses"],
    queryFn: () => api.get<Course[]>("/courses"),
  });
  const stale = useQuery({
    queryKey: ["study-stale", STALE_DAYS],
    queryFn: () => api.get<StalePage>(`/study/stale${qs({ days: STALE_DAYS, limit: ROWS_PER_KIND })}`),
  });

  const loading = courses.isLoading || stale.isLoading;
  const failed = courses.isError || stale.isError;

  const courseRows = (courses.data ?? [])
    .filter((course) => course.status === "in_progress")
    .slice(0, ROWS_PER_KIND)
    .map((course) => ({
      id: `course-${course.id}`,
      kind: "Kurs",
      title: course.title,
      icon: <BookOpen size={13} />,
      href: `#/learning?view=courses&course=${course.id}`,
      detail: `%${course.progress_pct}`,
    }));

  const topicRows = (stale.data?.items ?? []).slice(0, ROWS_PER_KIND).map((topic) => {
    const age = topic.last_studied_at
      ? Math.floor((Date.now() - new Date(topic.last_studied_at).getTime()) / MS_PER_DAY)
      : null;
    return {
      id: `topic-${topic.id}`,
      kind: "Konu",
      title: topic.title,
      icon: <Brain size={13} />,
      href: `#/learning?focus=${topic.id}`,
      // Tazeleme tarihi varsa "tekrar zamani", yoksa bayatlama yasi gosterilir.
      detail: topic.next_review_at
        ? `Tekrar: ${new Date(topic.next_review_at).toLocaleDateString("tr-TR")}`
        : `Son çalışma: ${age === null ? "yok" : age <= 0 ? "bugün çalışıldı" : `${age} gün önce`}`,
    };
  });

  const rows = [...courseRows, ...topicRows];

  return (
    <Section title="Devam eden öğrenme" hint={loading ? undefined : `${rows.length} kayıt`}>
      {loading ? (
        <p role="status" className="py-4 text-center text-meta text-muted">
          Öğrenme kayıtları yükleniyor…
        </p>
      ) : failed ? (
        <p role="alert" className="py-4 text-center text-meta text-danger">
          Öğrenme kayıtları yüklenemedi.
        </p>
      ) : rows.length === 0 ? (
        <>
          <Empty>Devam eden kurs ya da tekrar bekleyen konu yok.</Empty>
          <p className="text-center">
            <a href="#/learning" className="text-meta text-accent">
              Öğrenmeye git
            </a>
          </p>
        </>
      ) : (
        <RowList as="ul">
          {rows.map((row) => (
            <li key={row.id} className="flex items-baseline justify-between gap-2 py-2">
              <a href={row.href} className="flex min-w-0 items-baseline gap-1.5">
                <span className="shrink-0 text-muted">{row.icon}</span>
                <span className="label-caps shrink-0 text-muted">{row.kind}</span>
                <span className="min-w-0 truncate text-body text-primary hover:text-accent">{row.title}</span>
              </a>
              <span className="shrink-0 text-meta text-muted">{row.detail}</span>
            </li>
          ))}
        </RowList>
      )}
    </Section>
  );
}
