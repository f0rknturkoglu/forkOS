/**
 * Konunun kaynaklari: URL listesi + tamamlama + ilerleme.
 *
 * Ilerleme yuzdesi BURADA HESAPLANMAZ -- backend kaynak sayacindan turetir
 * (alt konular dahil). Boylece agactaki yuzde ile detaydaki yuzde ayrisamaz.
 */
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpen, Dumbbell, ExternalLink, FileText, GraduationCap, Link2, Plus, Trash2, Video } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { safeHref } from "@/core/markdownParser";
import { Button, Chip, Empty, Field, IconButton, Input, RowList, Section, Select, cx } from "@/core/ui";
import type { LearningResource, TopicProgress } from "@/core/types";
import { useOnline } from "@/lib/hooks";

const KINDS = [
  { id: "link", label: "Bağlantı", icon: Link2 },
  { id: "video", label: "Video", icon: Video },
  { id: "article", label: "Makale", icon: FileText },
  { id: "course", label: "Kurs", icon: GraduationCap },
  { id: "book", label: "Kitap", icon: BookOpen },
  { id: "doc", label: "Doküman", icon: FileText },
  { id: "exercise", label: "Alıştırma", icon: Dumbbell },
] as const;

const kindOf = (id: string) => KINDS.find((k) => k.id === id) ?? KINDS[0];

function ProgressBar({ progress }: { progress: TopicProgress }) {
  const done = progress.total > 0 && progress.done === progress.total;
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between gap-3 text-meta">
        <span className="text-secondary">Öğrenme ilerlemesi</span>
        <span className={cx("numeral font-medium", done ? "text-ok" : "text-primary")}>
          {progress.done}/{progress.total} · %{progress.pct}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-control bg-surface-sunken">
        <div
          className={cx("h-full rounded-control transition-all", done ? "bg-ok" : "bg-accent")}
          style={{ width: `${progress.pct}%` }}
        />
      </div>
    </div>
  );
}

export function ResourceList({ topicId }: { topicId: string }) {
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [kind, setKind] = useState("link");
  const online = useOnline();

  const { data: resources = [] } = useQuery({
    queryKey: ["topic-resources", topicId],
    queryFn: () => api.get<LearningResource[]>(`/study/topics/${topicId}/resources`),
  });
  const { data: progress } = useQuery({
    queryKey: ["topic-progress", topicId],
    queryFn: () => api.get<TopicProgress>(`/study/topics/${topicId}/progress`),
  });

  const refresh = () => invalidateAfter("learning.write", "study.write");
  const add = useMutation({
    mutationFn: () => api.post(`/study/topics/${topicId}/resources`, { title, url: url.trim() || null, kind }),
    onSuccess: () => {
      setTitle("");
      setUrl("");
      refresh();
    },
  });
  const toggle = useMutation({
    mutationFn: ({ id, completed }: { id: string; completed: boolean }) =>
      api.patch(`/learning/resources/${id}`, { completed }),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/learning/resources/${id}`),
    onSuccess: refresh,
  });

  return (
    <Section title="Kaynaklar" hint={resources.length ? `${resources.length} materyal` : undefined}>
      {progress && progress.total > 0 && (
        <div className="mb-3 border-b border-subtle pb-3">
          <ProgressBar progress={progress} />
        </div>
      )}

      {resources.length === 0 ? (
        <Empty>Henüz kaynak yok. Aşağıdan bir URL ekle — tamamladıkça ilerleme dolar.</Empty>
      ) : (
        <RowList>
          {resources.map((resource) => {
            const meta = kindOf(resource.kind);
            const Icon = meta.icon;
            const done = resource.completed_at !== null;
            const href = resource.url ? safeHref(resource.url) : null;
            return (
              <div key={resource.id} className="flex items-center gap-2.5 py-2 text-body">
                {/* Tamamlama kutusu: ilerlemeyi bu belirler. */}
                <button
                  type="button"
                  title={done ? "Tamamlanmadı olarak işaretle" : "Tamamlandı olarak işaretle"}
                  disabled={!online}
                  onClick={() => toggle.mutate({ id: resource.id, completed: !done })}
                  className={cx(
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded-control border text-micro transition",
                    done ? "border-ok bg-ok text-canvas" : "border-strong hover:border-accent",
                    !online && "cursor-not-allowed opacity-40",
                  )}
                >
                  {done ? "✓" : ""}
                </button>
                <Icon size={14} className="shrink-0 text-muted" />
                <span className={cx("min-w-0 flex-1 truncate", done && "text-muted line-through")}>
                  {resource.title}
                </span>
                <Chip size="xs">{meta.label}</Chip>
                {href && (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={resource.url ?? ""}
                    className="shrink-0 text-muted transition hover:text-accent"
                  >
                    <ExternalLink size={14} />
                  </a>
                )}
                <IconButton
                  title="Kaynağı sil"
                  tone="danger"
                  disabled={!online}
                  onClick={() => remove.mutate(resource.id)}
                >
                  <Trash2 size={13} />
                </IconButton>
              </div>
            );
          })}
        </RowList>
      )}

      <form
        className="mt-3 grid items-end gap-2 border-t border-subtle pt-3 sm:grid-cols-[1fr_1fr_8rem_auto]"
        onSubmit={(event) => {
          event.preventDefault();
          if (title.trim()) add.mutate();
        }}
      >
        <Field label="Başlık">
          <Input value={title} onChange={setTitle} placeholder="MIT 18.06 ders 1" className="w-full" />
        </Field>
        <Field label="URL">
          <Input value={url} onChange={setUrl} placeholder="https://…" className="w-full" />
        </Field>
        <Field label="Tür">
          <Select value={kind} onChange={setKind} className="w-full">
            {KINDS.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </Select>
        </Field>
        <Button type="submit" variant="primary" disabled={!online || add.isPending}>
          <Plus size={14} /> Ekle
        </Button>
      </form>
    </Section>
  );
}
