import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Archive, FileAudio, ImagePlus, Mic, Pin, PinOff, Plus, Save, Search, Square, Trash2 } from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { api } from "@/core/api";
import { BacklinksPanel } from "@/core/BacklinksPanel";
import { invalidateAfter } from "@/core/invalidation";
import { Markdown } from "@/core/Markdown";
import { RelatedPanel } from "@/core/RelatedPanel";
import { confirmDialog } from "@/core/dialog";
import type { Note, NoteAttachment } from "@/core/types";
import {
  Button,
  Chip,
  Empty,
  FileInput,
  IconButton,
  Input,
  PageFrame,
  PageHeader,
  Section,
  Surface,
  Textarea,
  cx,
  useToast,
} from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { formatTrDateTime } from "@/lib/date";

const refreshNotes = () => invalidateAfter("note.write", "link.write");

function dateLabel(value: string): string {
  return formatTrDateTime(value, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function starterBody(title = "Yeni not"): string {
  return `# ${title}\n\n`;
}

export function NotesPage() {
  const route = useHashRoute();
  const focusId = route.params.get("focus") ?? "";
  const online = useOnline();
  const toast = useToast();
  const fileInput = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(focusId);
  const [creating, setCreating] = useState(route.params.get("new") === "1");
  const [draft, setDraft] = useState(() => (route.params.get("new") === "1" ? starterBody() : ""));
  // Draft'in ait oldugu not. Arka plan refetch'i secili notun YENI nesnesini
  // getirdiginde draft uzerine yazilmaz; yalnizca not id'si degistiginde yuklenir.
  const draftNoteId = useRef<string | null>(null);

  const { data: notes = [], isLoading } = useQuery({
    queryKey: ["notes"],
    queryFn: () => api.get<Note[]>("/notes"),
  });
  const selected = notes.find((note) => note.id === selectedId) ?? null;
  const visibleNotes = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("tr");
    if (!needle) return notes;
    return notes.filter((note) => `${note.title}\n${note.body}`.toLocaleLowerCase("tr").includes(needle));
  }, [notes, query]);

  useEffect(() => {
    if (focusId) {
      setSelectedId(focusId);
      setCreating(false);
    }
  }, [focusId]);

  useEffect(() => {
    if (creating) return;
    if (selected) {
      if (draftNoteId.current === selected.id) return;
      setDraft(selected.body);
      draftNoteId.current = selected.id;
      return;
    }
    if (!selectedId && notes[0]) {
      setSelectedId(notes[0].id);
      setDraft(notes[0].body);
      draftNoteId.current = notes[0].id;
    }
  }, [creating, notes, selected, selectedId]);

  const save = useMutation({
    mutationFn: () =>
      creating
        ? api.post<Note>("/notes", { body: draft.trim() })
        : api.patch<Note>(`/notes/${selectedId}`, { body: draft.trim() }),
    onSuccess: (note) => {
      setCreating(false);
      setSelectedId(note.id);
      setDraft(note.body);
      draftNoteId.current = note.id;
      refreshNotes();
      navigate(`/notes?focus=${note.id}`);
      toast.push("Not kaydedildi.", { tone: "ok" });
    },
    onError: () => toast.push("Not kaydedilemedi.", { tone: "danger" }),
  });

  const patch = useMutation({
    mutationFn: ({ id, pinned }: { id: string; pinned: boolean }) => api.patch<Note>(`/notes/${id}`, { pinned }),
    onSuccess: refreshNotes,
  });

  const archive = useMutation({
    mutationFn: (id: string) => api.post(`/notes/${id}/archive`),
    onSuccess: () => {
      setSelectedId("");
      setDraft("");
      draftNoteId.current = null;
      refreshNotes();
      navigate("/notes");
      toast.push("Not arşivlendi.", { tone: "ok" });
    },
  });

  const upload = useMutation({
    mutationFn: async (files: File[]) => {
      if (!selectedId) throw new Error("Önce notu kaydet");
      const uploaded: NoteAttachment[] = [];
      for (const file of files) {
        uploaded.push(await api.upload<NoteAttachment>(`/notes/${selectedId}/attachments`, file));
      }
      return uploaded;
    },
    onSuccess: (items) => {
      refreshNotes();
      toast.push(`${items.length} ek yüklendi.`, { tone: "ok" });
    },
    onError: (error: Error) => toast.push(error.message || "Ek yüklenemedi.", { tone: "danger" }),
  });

  const removeAttachment = useMutation({
    mutationFn: (attachmentId: string) => api.del(`/notes/${selectedId}/attachments/${attachmentId}`),
    onSuccess: refreshNotes,
  });

  const dirty = creating ? Boolean(draft.trim()) : Boolean(selected && draft !== selected.body);
  const beginNote = async (title?: string) => {
    if (dirty) {
      const ok = await confirmDialog({
        title: "Kaydedilmemiş değişiklikler var",
        body: "Yeni nota geçerseniz mevcut değişiklikler kaybolacak. Yine de devam edilsin mi?",
        confirmLabel: "Değişiklikleri At ve Yeni Not Aç",
        tone: "danger",
      });
      if (!ok) return;
    }
    setCreating(true);
    setSelectedId("");
    setDraft(starterBody(title));
    draftNoteId.current = null;
    navigate("/notes?new=1");
  };
  const openNote = async (note: Note) => {
    if (note.id === selectedId && !creating) return;
    if (dirty) {
      const ok = await confirmDialog({
        title: "Kaydedilmemiş değişiklikler var",
        body: "Başka bir nota geçerseniz mevcut değişiklikler kaybolacak. Yine de devam edilsin mi?",
        confirmLabel: "Değişiklikleri At ve Geç",
        tone: "danger",
      });
      if (!ok) return;
    }
    setCreating(false);
    setSelectedId(note.id);
    setDraft(note.body);
    draftNoteId.current = note.id;
    navigate(`/notes?focus=${note.id}`);
  };

  return (
    <PageFrame className="space-y-5">
      <PageHeader
        eyebrow="Kaynaklar"
        title="Notlar"
        action={
          <Button variant="primary" onClick={() => beginNote()}>
            <Plus size={14} /> Yeni not
          </Button>
        }
      />
      <p className="text-meta text-muted">
        Markdown yaz, <span className="font-mono">[[başka bir kayıt]]</span> ile bağla; fotoğraf ve sesleri notunla
        birlikte yerelde tut.
      </p>

      <div className="grid gap-4 lg:grid-cols-4">
        <Surface className="min-w-0 p-3 lg:col-span-1">
          <div className="mb-3 flex items-center gap-2">
            <Search size={14} className="shrink-0 text-icon" />
            <Input value={query} onChange={setQuery} placeholder="Notlarda ara" className="min-w-0 flex-1" />
          </div>
          <div className="max-h-screen space-y-1 overflow-y-auto pr-1">
            {isLoading ? (
              <p className="p-3 text-meta text-muted">Notlar yükleniyor…</p>
            ) : visibleNotes.length === 0 ? (
              <Empty>{query ? "Eşleşen not yok." : "İlk notunu oluştur."}</Empty>
            ) : (
              visibleNotes.map((note) => (
                <button
                  key={note.id}
                  type="button"
                  onClick={() => openNote(note)}
                  className={cx(
                    "w-full rounded-control border px-3 py-2.5 text-left transition",
                    selectedId === note.id && !creating
                      ? "border-accent-border bg-accent-surface"
                      : "border-transparent hover:border-subtle hover:bg-surface-hover",
                  )}
                >
                  <span className="flex items-center gap-1.5 text-body text-primary">
                    <span className="min-w-0 flex-1 truncate">{note.title}</span>
                    {note.pinned && <Pin size={11} className="shrink-0 text-accent" />}
                  </span>
                  <span className="mt-1 block truncate text-meta text-muted">{dateLabel(note.updated_at)}</span>
                </button>
              ))
            )}
          </div>
        </Surface>

        <div className="min-w-0 space-y-4 lg:col-span-3">
          {!creating && !selected ? (
            <Surface className="flex min-h-96 items-center justify-center p-6">
              <Empty variant="page" title="Bir not seç">
                Soldan bir not aç veya yeni bir düşünce yakala.
              </Empty>
            </Surface>
          ) : (
            <>
              <Surface className="p-3">
                <div className="mb-3 flex flex-wrap items-center gap-2 border-b border-subtle pb-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-heading text-primary">{creating ? "Yeni not" : selected?.title}</p>
                    <p className="text-meta text-muted">
                      {dirty
                        ? "Kaydedilmemiş değişiklik"
                        : selected
                          ? `Son düzenleme ${dateLabel(selected.updated_at)}`
                          : ""}
                    </p>
                  </div>
                  {!creating && selected && (
                    <>
                      <IconButton
                        title={selected.pinned ? "Sabitlemeyi kaldır" : "Sabitle"}
                        disabled={!online}
                        onClick={() => patch.mutate({ id: selected.id, pinned: !selected.pinned })}
                      >
                        {selected.pinned ? <PinOff size={14} /> : <Pin size={14} />}
                      </IconButton>
                      <IconButton title="Arşivle" disabled={!online} onClick={() => archive.mutate(selected.id)}>
                        <Archive size={14} />
                      </IconButton>
                    </>
                  )}
                  <Button
                    variant="primary"
                    disabled={!online || !draft.trim() || !dirty || save.isPending}
                    onClick={() => save.mutate()}
                  >
                    <Save size={14} /> {save.isPending ? "Kaydediliyor" : "Kaydet"}
                  </Button>
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                  <div>
                    <p className="mb-2 label-caps text-secondary">Markdown</p>
                    <Textarea
                      value={draft}
                      onChange={setDraft}
                      ariaLabel="Not içeriği"
                      placeholder="# Başlık\n\nDüşünceni yaz…"
                      className="min-h-96 w-full font-mono"
                      onKeyDown={(event) => {
                        if ((event.metaKey || event.ctrlKey) && event.key.toLocaleLowerCase("tr") === "s") {
                          event.preventDefault();
                          if (online && dirty && draft.trim()) save.mutate();
                        }
                      }}
                    />
                  </div>
                  <div className="min-h-96 rounded-card border border-subtle bg-surface-sunken p-4">
                    <div className="mb-3 flex items-center justify-between border-b border-subtle pb-2">
                      <p className="label-caps text-secondary">Önizleme</p>
                      <Chip>Markdown</Chip>
                    </div>
                    <Markdown
                      source={draft}
                      links={selected?.resolved_links ?? []}
                      unresolved={selected?.unresolved_links ?? []}
                      onMissingClick={(target) => beginNote(target)}
                    />
                  </div>
                </div>
              </Surface>

              {!creating && selected && (
                <Section
                  title="Fotoğraf ve ses"
                  hint={`${selected.attachments?.length ?? 0} ek`}
                  action={
                    <div className="flex items-center gap-1.5">
                      <FileInput
                        ref={fileInput}
                        accept="image/jpeg,image/png,image/webp,image/gif,audio/*"
                        multiple
                        onChange={(event) => {
                          const files = Array.from(event.target.files ?? []);
                          if (files.length) upload.mutate(files);
                          event.target.value = "";
                        }}
                      />
                      <Button disabled={!online || upload.isPending} onClick={() => fileInput.current?.click()}>
                        <ImagePlus size={14} /> Dosya ekle
                      </Button>
                      <VoiceRecorder
                        disabled={!online || upload.isPending}
                        onFile={(file) => upload.mutate([file])}
                        onError={(message) => toast.push(message, { tone: "danger" })}
                      />
                    </div>
                  }
                >
                  <AttachmentGallery
                    attachments={selected.attachments ?? []}
                    removing={removeAttachment.isPending}
                    onRemove={(id) => removeAttachment.mutate(id)}
                  />
                </Section>
              )}

              {!creating && selected && (
                <div className="grid gap-4 xl:grid-cols-2">
                  <RelatedPanel entityId={selected.id} />
                  <BacklinksPanel entityId={selected.id} />
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </PageFrame>
  );
}

function AttachmentGallery({
  attachments,
  removing,
  onRemove,
}: {
  attachments: NoteAttachment[];
  removing: boolean;
  onRemove: (id: string) => void;
}) {
  if (attachments.length === 0) {
    return <Empty>Bu notta henüz medya yok. Fotoğraf seçebilir veya doğrudan ses kaydedebilirsin.</Empty>;
  }
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {attachments.map((attachment) => (
        <Surface key={attachment.id} className="overflow-hidden">
          {attachment.mime.startsWith("image/") ? (
            <img
              src={attachment.url}
              alt={attachment.name}
              className="aspect-video w-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="space-y-3 p-3">
              <span className="flex items-center gap-2 text-body text-primary">
                <FileAudio size={16} className="text-icon" />
                <span className="min-w-0 truncate">{attachment.name}</span>
              </span>
              <audio controls preload="metadata" src={attachment.url} className="w-full" />
            </div>
          )}
          <div className="flex items-center gap-2 border-t border-subtle px-3 py-2">
            <span className="min-w-0 flex-1 truncate text-meta text-muted">
              {attachment.name} · {Math.max(1, Math.round(attachment.size / 1024))} KB
            </span>
            <IconButton title="Eki sil" tone="danger" disabled={removing} onClick={() => onRemove(attachment.id)}>
              <Trash2 size={13} />
            </IconButton>
          </div>
        </Surface>
      ))}
    </div>
  );
}

function VoiceRecorder({
  disabled,
  onFile,
  onError,
}: {
  disabled: boolean;
  onFile: (file: File) => void;
  onError: (message: string) => void;
}) {
  const [recording, setRecording] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(
    () => () => {
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((track) => track.stop());
    },
    [],
  );

  const start = async () => {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      onError("Bu tarayıcı ses kaydını desteklemiyor.");
      return;
    }
    try {
      const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      const nextRecorder = new MediaRecorder(audioStream, mime ? { mimeType: mime } : undefined);
      chunks.current = [];
      stream.current = audioStream;
      recorder.current = nextRecorder;
      nextRecorder.ondataavailable = (event) => {
        if (event.data.size) chunks.current.push(event.data);
      };
      nextRecorder.onstop = () => {
        const type = nextRecorder.mimeType || "audio/webm";
        const blob = new Blob(chunks.current, { type });
        stream.current?.getTracks().forEach((track) => track.stop());
        stream.current = null;
        recorder.current = null;
        setRecording(false);
        if (blob.size) onFile(new File([blob], `ses-notu-${Date.now()}.webm`, { type }));
      };
      nextRecorder.start();
      setRecording(true);
    } catch {
      onError("Mikrofon açılamadı; tarayıcı iznini kontrol et.");
    }
  };

  const stop = () => recorder.current?.stop();
  return recording ? (
    <Button variant="danger" onClick={stop}>
      <Square size={13} /> Kaydı bitir
    </Button>
  ) : (
    <Button disabled={disabled} onClick={start}>
      <Mic size={14} /> Ses kaydet
    </Button>
  );
}
