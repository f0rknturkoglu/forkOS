import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Chip, Empty, RowList, Section } from "@/core/ui";
import type { Course } from "@/core/types";

/** Devam eden kurslar (kitaplar Faz 11'de Medya'da). */
export function LearningWidget() {
  const { data: courses = [] } = useQuery({ queryKey: ["courses"], queryFn: () => api.get<Course[]>("/courses") });

  const activeCourses = courses.filter((c) => c.status === "in_progress").slice(0, 3);
  const rows: { id: string; title: string; detail: string }[] = activeCourses.map((c) => ({
    id: c.id,
    title: c.title,
    detail: `%${Math.round(c.progress_pct)}`,
  }));
  return (
    <Section title="Devam eden öğrenme">
      {rows.length === 0 ? (
        <Empty>Devam eden kurs yok.</Empty>
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
