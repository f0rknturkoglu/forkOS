/**
 * Konunun notlari: markdown govde + [[wikilink]] + #etiket.
 *
 * Notlar konuya `notes_about` ile baglanir. Iki aksiyon BILEREK ayrildi:
 *   - "Konudan ayır"     yalnizca `notes_about` bagini kaldirir (not yasar,
 *                        Notlar sayfasinda kalmaya devam eder).
 *   - "Notu tamamen sil" not entity'sini sistemden siler (geri alinamaz).
 * Yanlis aksiyonla global bir notun silinmesi bu ayrimla imkansizdir.
 *
 * YAZMA TEK YERDEDIR: burada ikinci bir editor acilmaz. "Not al" baslangic
 * metnini alir, notu konuya baglar ve Notlar modulunde acar
 * (`/notes?focus=<id>`) -- medya detayindaki NoteComposer ile ayni desen.
 * Boylece slash komutlari, klasor, ek havuzu ve tuval ayni editorden gelir;
 * "Notu duzenle" de ayni tam deneyime gider.
 */
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link2Off, Pencil, Plus, Trash2 } from "lucide-react";
import { api, qs } from "@/core/api";
import { navigate } from "@/app/router";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import { Markdown } from "@/core/Markdown";
import {
  Button,
  Chip,
  Empty,
  Field,
  IconButton,
  Input,
  Modal,
  SectionHeader,
  SkeletonRows,
  Textarea,
  relativeTime,
  useToast,
} from "@/core/ui";
import type { Note } from "@/core/types";
import { useOnline } from "@/lib/hooks";

/** Notu tam editorde acar: tek yazma yuzeyi Notlar moduludur. */
function openInNotes(noteId: string): void {
  void navigate(`/notes?focus=${encodeURIComponent(noteId)}`);
}

export function TopicNotes({
  topicId,
  topicTitle,
  noteCount,
  composeSignal = 0,
}: {
  topicId: string;
  /** Kompozisyon penceresinin basligi -- konu adi baglami kurar. */
  topicTitle?: string;
  /** Konu detayindan gelen `note_count` -- liste ile ayni sayiyi gosterir. */
  noteCount?: number;
  /** Dis aksiyon ("Not al") besteciyi acar; her artis yeni bir istek. */
  composeSignal?: number;
}) {
  const [composing, setComposing] = useState(false);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftLine, setDraftLine] = useState("");
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

  /** Not konuya baglanir, sonra tam editorde acilir. */
  const create = useMutation({
    mutationFn: (body: string) => api.post<Note>("/notes", { body, relate_to: topicId }),
    onSuccess: (note) => {
      invalidateAfter("note.write");
      setComposing(false);
      setDraftTitle("");
      setDraftLine("");
      toast.push("Not oluşturuldu ve konuya bağlandı.", { tone: "ok" });
      openInNotes(note.id);
    },
    onError: (error: Error) => toast.push(`Not oluşturulamadı: ${error.message}`, { tone: "danger" }),
  });

  const body = [draftTitle.trim(), draftLine.trim()].filter(Boolean).join("\n\n");

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
                {/* Tam editor: slash komutlari, klasor, ek havuzu ve tuval orada. */}
                <IconButton title="Notu düzenle (Notlar sayfasında)" onClick={() => openInNotes(note.id)}>
                  <Pencil size={13} />
                </IconButton>
                {/* Bag kaldirma: not yasar. */}
                <IconButton
                  title="Konudan ayır (not silinmez)"
                  disabled={!online || detach.isPending}
                  onClick={() => void confirmDetach(note)}
                >
                  <Link2Off size={13} />
                </IconButton>
                {/* Entity silme: geri alinamaz. */}
                <IconButton
                  title="Notu tamamen sil"
                  tone="danger"
                  disabled={!online || remove.isPending}
                  onClick={() => void confirmRemove(note)}
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

      <Modal
        open={composing}
        onClose={() => setComposing(false)}
        title="Yeni not"
        hint={
          topicTitle
            ? `${topicTitle} · başlangıç metni; gövdeyi Notlar editöründe yazarsın`
            : "Başlangıç metni; gövdeyi Notlar editöründe yazarsın"
        }
        footer={
          <div className="flex flex-wrap justify-end gap-2">
            <Button size="sm" onClick={() => setComposing(false)} disabled={create.isPending}>
              Vazgeç
            </Button>
            <Button
              size="sm"
              variant="primary"
              disabled={!online || create.isPending || body.length === 0}
              onClick={() => create.mutate(body)}
            >
              Notu oluştur ve aç
            </Button>
          </div>
        }
      >
        <div className="space-y-3">
          <Field label="Not başlığı">
            <Input
              value={draftTitle}
              onChange={setDraftTitle}
              autoFocus
              disabled={create.isPending}
              ariaLabel="Not başlığı"
              placeholder={topicTitle ? `${topicTitle} notları` : "Not başlığı"}
              className="w-full"
            />
          </Field>
          <Field label="İlk satır" hint="Başlık ve ilk satır boşsa not oluşturulamaz.">
            <Textarea
              rows={4}
              value={draftLine}
              onChange={setDraftLine}
              disabled={create.isPending}
              ariaLabel="İlk satır"
              placeholder="Aklında kalan ilk şey… [[bağlantı]] ve #etiket gövdede serbest."
            />
          </Field>
        </div>
      </Modal>
    </div>
  );
}
