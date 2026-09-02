/**
 * Konunun notlari: markdown govde + [[wikilink]] + #etiket.
 *
 * Notlar konuya `notes_about` ile baglanir; govdedeki wikilink'ler ayrica
 * `mentions` uretir ve backlink panelinde/grafta gorunur.
 */
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { api, qs } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Markdown } from "@/core/Markdown";
import { NoteEditor } from "@/core/NoteEditor";
import { confirmDialog } from "@/core/dialog";
import { Button, Chip, Empty, IconButton, Section, relativeTime } from "@/core/ui";
import type { Note } from "@/core/types";
import { useOnline } from "@/lib/hooks";

export function TopicNotes({ topicId, onOpenTag }: { topicId: string; onOpenTag?: (tag: string) => void }) {
  const [composing, setComposing] = useState(false);
  const [editing, setEditing] = useState<Note | null>(null);
  const online = useOnline();

  const { data: notes = [] } = useQuery({
    queryKey: ["notes", "about", topicId],
    queryFn: () => api.get<Note[]>("/notes" + qs({ about: topicId })),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/notes/${id}`),
    onSuccess: () => invalidateAfter("note.write"),
  });

  const confirmRemove = async (note: Note) => {
    const ok = await confirmDialog({
      title: `"${note.title}" silinsin mi?`,
      body: "Nottan gelen bağlantılar da kalkar.",
      confirmLabel: "Sil",
      tone: "danger",
    });
    if (ok) remove.mutate(note.id);
  };

  if (editing) {
    return <NoteEditor note={editing} onDone={() => setEditing(null)} onCancel={() => setEditing(null)} />;
  }
  if (composing) {
    return <NoteEditor relateTo={topicId} onDone={() => setComposing(false)} onCancel={() => setComposing(false)} />;
  }

  return (
    <Section
      title="Notlar"
      hint={notes.length ? `${notes.length} not` : undefined}
      action={
        <Button size="sm" variant="primary" disabled={!online} onClick={() => setComposing(true)}>
          <Plus size={13} /> Not ekle
        </Button>
      }
    >
      {notes.length === 0 ? (
        <Empty>Bu konuda not yok. Markdown yazabilir, [[başka konu]] ile bağ kurabilir, #etiket verebilirsin.</Empty>
      ) : (
        <div className="space-y-4">
          {notes.map((note) => (
            <article key={note.id} className="rounded-card border border-subtle bg-surface p-3.5">
              <header className="mb-2 flex items-center gap-2 border-b border-subtle pb-2">
                <h3 className="min-w-0 flex-1 truncate text-heading text-primary">{note.title}</h3>
                <span className="shrink-0 text-meta text-muted">{relativeTime(note.updated_at)}</span>
                <IconButton title="Düzenle" disabled={!online} onClick={() => setEditing(note)}>
                  <Pencil size={13} />
                </IconButton>
                <IconButton title="Sil" tone="danger" disabled={!online} onClick={() => confirmRemove(note)}>
                  <Trash2 size={13} />
                </IconButton>
              </header>
              <Markdown
                source={note.body}
                links={note.resolved_links ?? []}
                unresolved={note.unresolved_links ?? []}
                onTagClick={onOpenTag}
              />
              {(note.tags ?? []).length > 0 && (
                <footer className="mt-2.5 flex flex-wrap gap-1.5 border-t border-subtle pt-2.5">
                  {(note.tags ?? []).map((tag) => (
                    <Chip key={tag} size="xs">
                      #{tag}
                    </Chip>
                  ))}
                </footer>
              )}
            </article>
          ))}
        </div>
      )}
    </Section>
  );
}
