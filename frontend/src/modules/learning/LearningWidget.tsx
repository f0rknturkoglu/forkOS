import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { Course, StudyTopic } from "@/core/types";
import { Empty, RowList, Section } from "@/core/ui";

/**
 * Ogrenme widget'i (Faz 12: study + learning birlesik).
 * Iki ayri kutu yerine tek liste: devam eden kurslar + tekrar bekleyen
 * konular. Konu satirinin yaninda varsa bagli kaynak sayisi yok --
 * tiklayinca sayfada RelatedPanel zaten kaynaklari gosterir.
 */
export function LearningWidget() {
  const { data: courses = [] } = useQuery({
    queryKey: ["courses"],
    queryFn: () => api.get<Course[]>("/courses"),
  });
  const { data: stale = [] } = useQuery({
    queryKey: ["study-stale"],
    queryFn: () => api.get<StudyTopic[]>("/study/stale?days=21"),
  });

  const rows: { id: string; title: string; detail: string }[] = [
    ...courses
      .filter((c) => c.status === "in_progress")
      .slice(0, 3)
      .map((c) => ({ id: c.id, title: c.title, detail: `%${Math.round(c.progress_pct)}` })),
    ...stale.slice(0, 3).map((t) => ({
      id: t.id,
      title: t.title,
      detail: t.last_studied_at ? new Date(t.last_studied_at).toLocaleDateString("tr-TR") : "yeni",
    })),
  ];

  return (
    <Section title="Devam eden öğrenme">
      {rows.length === 0 ? (
        <Empty>Devam eden kurs ya da tekrar bekleyen konu yok.</Empty>
      ) : (
        <RowList>
          {rows.map((row) => (
            <div key={row.id} className="flex items-baseline justify-between gap-2 py-2 text-meta">
              <a href="#/learning" className="min-w-0 truncate text-body text-primary hover:text-accent">
                {row.title}
              </a>
              <span className="shrink-0 text-muted">{row.detail}</span>
            </div>
          ))}
        </RowList>
      )}
    </Section>
  );
}
