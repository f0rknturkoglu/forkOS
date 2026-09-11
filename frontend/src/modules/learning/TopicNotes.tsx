/**
 * Konunun notlari: markdown govde + [[wikilink]] + #etiket.
 *
 * Notlar konuya `notes_about` ile baglanir. Iki aksiyon BILEREK ayrildi:
 *   - "Konudan ayır"     yalnizca `notes_about` bagini kaldirir (not yasar,
 *                        Notlar sayfasinda kalmaya devam eder).
 *   - "Notu tamamen sil" not entity'sini sistemden siler (geri alinamaz).
 * Yanlis aksiyonla global bir notun silinmesi bu ayrimla imkansizdir.
 *
 * Editor tektir: merkezi `NoteEditor` (Faz 2 kurali -- ikinci editör yok).
 */
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link2Off, Pencil, Plus, Trash2 } from "lucide-react";
import { api, qs } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import { Markdown } from "@/core/Markdown";
import { NoteEditor } from "@/core/NoteEditor";
import { Button, Chip, Empty, IconButton, SectionHeader, SkeletonRows, relativeTime, useToast } from "@/core/ui";
import type { Note } from "@/core/types";
import { useOnline } from "@/lib/hooks";

export function TopicNotes({
  topicId,
  noteCount,
  composeSignal = 0,
}: {
  topicId: string;
  /** Konu detayindan gelen `note_count` -- liste ile ayni sayiyi gosterir. */
  noteCount?: number;
  /** Dis aksiyon ("Not al") editoru acar; her artis yeni bir istek. */
  composeSignal?: number;
}) {
  const [composing, setComposing] = useState(false);
  const [editing, setEditing] = useState<Note | null>(null);
  /* Etiket filtresi: #etiket ya da govdedeki etikete tiklamak listeyi suzer. */
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const online = useOnline();
  const toast = useToast();

  useEffect(() => {
    if (composeSignal > 0) setComposing(true);
  }, [composeSignal]);

  const { data: notes = [], isLoading } = useQuery({
    queryKey: ["notes", "about", topicId],
    queryFn: () => api.get<Note[]>("/notes" + qs({ about: topicId })),
  });

  /** Yalnizca bag kaldirilir; not entity'sine dokunulmaz. */
  const detach = useMutation({
    mutationFn: (note: Note) => api.del("/links", { from_id: note.id, to_id: topicId, relation: "notes_about" }),
    onSuccess: () => {
      invalidateAfter("link.write", "note.write");
      toast.push("Bağ kaldırıldı — not silinmedi, Notlar sayfasında duruyor.", { tone: "ok" });
    },
  });

  /** Not entity'sini sistemden siler. */
  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/notes/${id}`),
    onSuccess: () => {
      invalidateAfter("note.write");
      toast.push("Not sistemden silindi.", { tone: "danger" });
    },
  });

  const confirmDetach = async (note: Note) => {
    const ok = await confirmDialog({
      title: `"${note.title}" bu konudan ayrılsın mı?`,
      body: "Not silinmez; yalnızca bu konuyla bağı kaldırılır ve not Notlar sayfasında kalır.",
      confirmLabel: "Konudan ayır",
    });
    if (ok) detach.mutate(note);
  };

  const confirmRemove = async (note: Note) => {
    const ok = await confirmDialog({
      title: `"${note.title}" tamamen silinsin mi?`,
      body: "Bu not sistemden silinecek; etiketleri, bağlantıları ve içeriği geri getirilemez.",
      confirmLabel: "Notu tamamen sil",
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

  const visible = tagFilter ? notes.filter((note) => (note.tags ?? []).includes(tagFilter)) : notes;

  return (
    <div className="space-y-4">
      <SectionHeader
        label="Notlar"
        hint={`${noteCount ?? notes.length} not`}
        action={
          <Button size="sm" variant="primary" disabled={!online} onClick={() => setComposing(true)}>
            <Plus size={13} /> Not al
          </Button>
        }
      />

      {tagFilter && (
        <div className="flex items-center gap-2">
          <span className="text-meta text-muted">Etiket filtresi:</span>
          <button type="button" onClick={() => setTagFilter(null)} aria-label="Etiket filtresini temizle">
            <Chip size="xs" tone="accent">
              #{tagFilter} ✕
            </Chip>
          </button>
        </div>
      )}

      {isLoading ? (
        <SkeletonRows rows={2} />
      ) : notes.length === 0 ? (
        <Empty>Bu konuda not yok. Markdown yazabilir, [[başka konu]] ile bağ kurabilir, #etiket verebilirsin.</Empty>
      ) : visible.length === 0 ? (
        <Empty>Bu etikette not yok.</Empty>
      ) : (
        <div className="space-y-4">
          {visible.map((note) => (
            <article key={note.id} className="rounded-card border border-subtle bg-surface p-3.5">
              <header className="mb-2 flex items-center gap-2 border-b border-subtle pb-2">
                <h3 className="min-w-0 flex-1 truncate text-heading text-primary">{note.title}</h3>
                <span className="shrink-0 text-meta text-muted">{relativeTime(note.updated_at)}</span>
                <IconButton title="Notu düzenle" disabled={!online} onClick={() => setEditing(note)}>
                  <Pencil size={13} />
                </IconButton>
                {/* Bag kaldirma: not yasar. */}
                <IconButton
                  title="Konudan ayır (not silinmez)"
                  disabled={!online || detach.isPending}
                  onClick={() => confirmDetach(note)}
                >
                  <Link2Off size={13} />
                </IconButton>
                {/* Entity silme: geri alinamaz. */}
                <IconButton
                  title="Notu tamamen sil"
                  tone="danger"
                  disabled={!online || remove.isPending}
                  onClick={() => confirmRemove(note)}
                >
                  <Trash2 size={13} />
                </IconButton>
              </header>
              <Markdown
                source={note.body}
                links={note.resolved_links ?? []}
                unresolved={note.unresolved_links ?? []}
                onTagClick={setTagFilter}
              />
              {(note.tags ?? []).length > 0 && (
                <footer className="mt-2.5 flex flex-wrap gap-1.5 border-t border-subtle pt-2.5">
                  {(note.tags ?? []).map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      aria-pressed={tagFilter === tag}
                      onClick={() => setTagFilter((current) => (current === tag ? null : tag))}
                      className="shrink-0"
                    >
                      <Chip size="xs" tone={tagFilter === tag ? "accent" : "neutral"}>
                        #{tag}
                      </Chip>
                    </button>
                  ))}
                </footer>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
