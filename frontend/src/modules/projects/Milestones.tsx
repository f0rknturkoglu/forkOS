import { invalidateAfter } from "@/core/invalidation";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Check, Plus, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { Button, Empty, IconButton, Input, RowList, Section, cx } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { Project } from "@/core/types";

/** Kilometre taslari -- projenin buyuk adimlari, gorevlerden bir tik yukarisi. */
export function Milestones({ project }: { project: Project }) {
  const [title, setTitle] = useState("");
  const online = useOnline();
  const refresh = () => invalidateAfter("project.write");

  const add = useMutation({
    mutationFn: () => api.post(`/projects/${project.id}/milestones`, { title: title.trim() }),
    onSuccess: () => {
      setTitle("");
      refresh();
    },
  });
  const toggle = useMutation({
    mutationFn: ({ id, completed }: { id: string; completed: boolean }) =>
      api.patch(`/milestones/${id}`, { completed }),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/milestones/${id}`),
    onSuccess: refresh,
  });

  const items = project.milestones ?? [];
  const doneCount = items.filter((item) => item.completed_at).length;

  return (
    <Section title="Kilometre taşları" hint={items.length ? `${doneCount}/${items.length}` : undefined}>
      <form
        className="mb-3 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (title.trim()) add.mutate();
        }}
      >
        <Input
          value={title}
          onChange={setTitle}
          placeholder="Yeni kilometre taşı"
          className="min-w-0 flex-1"
          ariaLabel="Kilometre taşı"
        />
        <Button type="submit" size="sm" disabled={!online || !title.trim() || add.isPending}>
          <Plus size={13} /> Ekle
        </Button>
      </form>

      {items.length === 0 ? (
        <Empty>Henüz kilometre taşı yok.</Empty>
      ) : (
        <RowList as="ul">
          {items.map((item) => {
            const done = Boolean(item.completed_at);
            return (
              <li key={item.id} className="group flex items-center gap-2.5 py-2">
                <button
                  type="button"
                  disabled={!online}
                  onClick={() => toggle.mutate({ id: item.id, completed: !done })}
                  aria-label={done ? "Tamamlanmadı olarak işaretle" : "Tamamla"}
                  className={cx(
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition",
                    done
                      ? "border-ok bg-ok text-canvas"
                      : "border-strong text-transparent hover:border-accent hover:text-accent",
                  )}
                >
                  <Check size={12} strokeWidth={3} />
                </button>
                <span
                  className={cx("min-w-0 flex-1 truncate text-body", done ? "text-muted line-through" : "text-primary")}
                >
                  {item.title}
                </span>
                {item.due_at && (
                  <span className="shrink-0 text-meta text-muted">
                    {new Date(item.due_at).toLocaleDateString("tr-TR", { day: "numeric", month: "short" })}
                  </span>
                )}
                <IconButton
                  title="Sil"
                  tone="danger"
                  disabled={!online}
                  onClick={() => remove.mutate(item.id)}
                  className="h-7 w-7 opacity-0 transition group-hover:opacity-100"
                >
                  <Trash2 size={13} />
                </IconButton>
              </li>
            );
          })}
        </RowList>
      )}
    </Section>
  );
}
