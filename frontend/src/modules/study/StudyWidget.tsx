import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { StudyTopic } from "@/core/types";
import { RowList, Section } from "@/core/ui";

export function StudyWidget() {
  const { data = [] } = useQuery({
    queryKey: ["study-stale"],
    queryFn: () => api.get<StudyTopic[]>("/study/stale?days=21"),
  });
  return (
    <Section title="Tekrar bekleyen konular">
      {data.length === 0 ? (
        <span className="text-meta text-muted">Bekleyen konu yok.</span>
      ) : (
        <RowList>
          {data.slice(0, 5).map((t) => (
            <div key={t.id} className="flex justify-between gap-3 py-2 text-meta">
              <span className="truncate">{t.title}</span>
              <span className="shrink-0 text-muted">
                {t.last_studied_at ? new Date(t.last_studied_at).toLocaleDateString("tr-TR") : "yeni"}
              </span>
            </div>
          ))}
        </RowList>
      )}
    </Section>
  );
}
