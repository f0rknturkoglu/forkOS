import { invalidateAfter } from "@/core/invalidation";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Archive, Pin, PinOff, Plus, StickyNote } from "lucide-react";
import { api } from "@/core/api";
import { Button, Empty, IconButton, Input, RowList, Section, Textarea, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { Note } from "@/core/types";

/** Not ile ilgili yazma olayi: liste + iliskiler tazelenir. */
const refreshNotes = () => invalidateAfter("note.write", "link.write");

/**
 * Yerel Notlar (Faz 21). Documents sayfasinda "Drive Belgeleri" ile yan
 * yana durur; ayri sidebar modulu yoktur. Hizli yakalama, pin, satir ici
 * duzenleme, arsivleme -- hepsi Entity yasam dongusu + event uzerinden.
 */
export function NotesSection({ online }: { online: boolean }) {
  const toast = useToast();
  const [draft, setDraft] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState("");

  const { data: notes = [] } = useQuery({
    queryKey: ["notes"],
    queryFn: () => api.get<Note[]>("/notes"),
  });

  const create = useMutation({
    mutationFn: () => api.post<Note>("/notes", { body: draft.trim() }),
    onSuccess: (note) => {
      setDraft("");
      refreshNotes();
      toast.push(`Not eklendi: ${note.title}`, { tone: "ok" });
    },
    onError: () => toast.push("Not eklenemedi.", { tone: "danger" }),
  });

  const patch = useMutation({
    mutationFn: ({ id, body, pinned }: { id: string; body?: string; pinned?: boolean }) =>
      api.patch<Note>(`/notes/${id}`, { body, pinned }),
    onSuccess: () => {
      setEditingId(null);
      refreshNotes();
    },
    onError: () => toast.push("Not güncellenemedi.", { tone: "danger" }),
  });

  const archive = useMutation({
    mutationFn: (id: string) => api.post(`/notes/${id}/archive`),
    onSuccess: () => {
      refreshNotes();
      toast.push("Not arşivlendi.", { tone: "ok" });
    },
  });

  return (
    <Section title="Yerel Notlar" hint={`${notes.length}`}>
      <div className="mb-3 flex items-center gap-2">
        <Input
          value={draft}
          onChange={setDraft}
          placeholder="Hızlı not al… (Enter ile ekle)"
          ariaLabel="Yeni not"
          onKeyDown={(event) => {
            if (event.key === "Enter" && draft.trim() && online) {
              event.preventDefault();
              create.mutate();
            }
          }}
          className="min-w-0 flex-1"
        />
        <Button
          size="sm"
          variant="primary"
          disabled={!online || !draft.trim() || create.isPending}
          onClick={() => create.mutate()}
        >
          <Plus size={13} /> Ekle
        </Button>
      </div>

      {notes.length === 0 ? (
        <Empty>Henüz not yok — bir düşünceyi yakala.</Empty>
      ) : (
        <RowList as="ul">
          {notes.map((note) => (
            <li key={note.id} className="px-3 py-2">
              {editingId === note.id ? (
                <div className="space-y-2">
                  <Textarea value={editBody} onChange={setEditBody} ariaLabel="Not içeriği" className="min-h-20" />
                  <div className="flex justify-end gap-1.5">
                    <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
                      Vazgeç
                    </Button>
                    <Button
                      size="sm"
                      variant="primary"
                      disabled={!online || !editBody.trim()}
                      onClick={() => patch.mutate({ id: note.id, body: editBody })}
                    >
                      Kaydet
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="group flex items-start gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingId(note.id);
                      setEditBody(note.body);
                    }}
                    className="min-w-0 flex-1 text-left"
                    aria-label={`${note.title} düzenle`}
                  >
                    <span className="flex items-center gap-1.5 text-body text-primary">
                      <StickyNote size={13} className="shrink-0 text-icon" />
                      <span className="truncate">{note.title}</span>
                      {note.pinned && <Pin size={11} className="shrink-0 text-accent" />}
                    </span>
                    <span className="block truncate whitespace-pre-line text-meta text-muted">
                      {note.body.length > 120 ? `${note.body.slice(0, 120)}…` : note.body}
                    </span>
                  </button>
                  <IconButton
                    title={note.pinned ? "Sabitlemeyi kaldır" : "Sabitle"}
                    disabled={!online || patch.isPending}
                    onClick={() => patch.mutate({ id: note.id, pinned: !note.pinned })}
                  >
                    {note.pinned ? <PinOff size={13} /> : <Pin size={13} />}
                  </IconButton>
                  <IconButton
                    title="Arşivle"
                    disabled={!online || archive.isPending}
                    onClick={() => archive.mutate(note.id)}
                  >
                    <Archive size={13} />
                  </IconButton>
                </div>
              )}
            </li>
          ))}
        </RowList>
      )}
    </Section>
  );
}
