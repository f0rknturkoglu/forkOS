import { Trash2 } from "lucide-react";
import type { Course } from "@/core/types";
import { Chip, IconButton, Range, RowList, Section } from "@/core/ui";

type Props = {
  courses: Course[];
  online: boolean;
  onProgress: (id: string, progress_pct: number) => void;
  onRemove: (id: string) => void;
};

export function CoursesTab({ courses, online, onProgress, onRemove }: Props) {
  return (
    <Section title="Kurslar">
      <RowList>
        {courses.map((c) => (
          <div
            key={c.id}
            className="group grid gap-2 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(180px,.7fr)] sm:items-center"
          >
            <div className="min-w-0">
              <p className="truncate text-body text-primary">{c.title}</p>
              <p className="text-meta text-muted">{c.platform ?? "Platform yok"}</p>
            </div>
            <div className="flex items-center gap-2">
              <Range
                value={c.progress_pct}
                min={0}
                max={100}
                disabled={!online}
                onChange={(n) => onProgress(c.id, n)}
                className="min-w-0 flex-1"
              />
              <Chip>{c.status}</Chip>
              <span className="text-meta">%{c.progress_pct}</span>
              <IconButton
                title="Sil"
                tone="danger"
                disabled={!online}
                className="shrink-0 opacity-0 transition group-hover:opacity-100"
                onClick={() => onRemove(c.id)}
              >
                <Trash2 size={14} />
              </IconButton>
            </div>
          </div>
        ))}
      </RowList>
    </Section>
  );
}
