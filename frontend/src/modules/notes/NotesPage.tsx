import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Archive,
  Brush,
  Eye,
  FileAudio,
  File as FileIcon,
  FileImage,
  FilePenLine,
  FolderKanban,
  Highlighter,
  Link2,
  Mic,
  Paperclip,
  Pencil,
  Pin,
  PinOff,
  Plus,
  Save,
  Square,
  Trash2,
} from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { api } from "@/core/api";
import { BacklinksPanel } from "@/core/BacklinksPanel";
import { invalidateAfter } from "@/core/invalidation";
import { Markdown } from "@/core/Markdown";
import { BEFORE_NAVIGATION_EVENT, type NavigationRequest } from "@/core/navigationGuard";
import { RelatedPanel } from "@/core/RelatedPanel";
import { NoteFlashcardPanel } from "@/modules/flashcard/NoteFlashcardPanel";
import { confirmDialog } from "@/core/dialog";
import type { Note, NoteAttachment, NoteFolder, Project } from "@/core/types";
import {
  Button,
  Chip,
  Empty,
  FileInput,
  IconButton,
  Kbd,
  PageFrame,
  Select,
  Surface,
  Textarea,
  cx,
  resolvedTheme,
  useToast,
  useTheme,
} from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { formatTrDateTime } from "@/lib/date";
import { CanvasErrorBoundary } from "./CanvasErrorBoundary";
import { BookmarkHighlights } from "./BookmarkHighlights";
import { NOTE_NAVIGATION_EVENT, type NoteNavigationRequest } from "./NoteSidebarTree";
import { SLASH_COMMANDS, SlashCommandMenu, slashContext, type SlashCommand } from "./SlashCommandMenu";

const refreshNotes = () => invalidateAfter("note.write", "link.write");

const NoteCanvas = lazy(async () => {
  // Excalidraw aksi halde font ve dil parcalarini unpkg CDN'inden ister.
  // Varliklar predev/prebuild adiminda public/ altina yerel kopyalanir.
  (window as Window & { EXCALIDRAW_ASSET_PATH?: string }).EXCALIDRAW_ASSET_PATH = "/excalidraw-assets/";
  return import("./NoteCanvas");
});

function dateLabel(value: string): string {
  return formatTrDateTime(value, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function starterBody(title = "Yeni not"): string {
  return `# ${title}\n\n`;
}

function attachmentLabel(name: string): string {
  return (
    name
      .replace(/[\[\]()]/g, " ")
      .replace(/\s+/g, " ")
      .trim() || "ek"
  );
}

export function attachmentMarkdown(attachment: NoteAttachment): string {
  const label = attachmentLabel(attachment.name);
  return attachment.mime.startsWith("image/") ? `![${label}](${attachment.url})` : `[${label}](${attachment.url})`;
}

export function insertMarkdownAt(source: string, position: number, markdown: string): { value: string; caret: number } {
  const at = Math.max(0, Math.min(position, source.length));
  const before = source.slice(0, at);
  const after = source.slice(at);
  const prefix = before && !before.endsWith("\n\n") ? (before.endsWith("\n") ? "\n" : "\n\n") : "";
  const suffix = after && !after.startsWith("\n\n") ? (after.startsWith("\n") ? "\n" : "\n\n") : "";
  const inserted = `${prefix}${markdown}${suffix}`;
  return { value: `${before}${inserted}${after}`, caret: before.length + prefix.length + markdown.length };
}

export function removeAttachmentMarkdown(source: string, attachment: NoteAttachment): string {
  const escapedUrl = attachment.url.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return source
    .replace(new RegExp(`!?\\[[^\\]\\n]*\\]\\(${escapedUrl}\\)`, "g"), "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function insertInlineAt(source: string, position: number, text: string): { value: string; caret: number } {
  const at = Math.max(0, Math.min(position, source.length));
  return { value: `${source.slice(0, at)}${text}${source.slice(at)}`, caret: at + text.length };
}

type EditorMode = "write" | "preview" | "canvas";
type PageWidth = NonNullable<Note["page_width"]>;
type UploadRequest = { files: File[]; at: number; source: string };

function AttachmentIcon({ attachment }: { attachment: NoteAttachment }) {
  if (attachment.mime.startsWith("image/")) return <FileImage size={14} />;
  if (attachment.mime.startsWith("audio/")) return <FileAudio size={14} />;
  return <FilePenLine size={14} />;
}

function AttachmentPool({
  attachments,
  disabled,
  onInsert,
  onRemove,
}: {
  attachments: NoteAttachment[];
  disabled: boolean;
  onInsert: (attachment: NoteAttachment) => void;
  onRemove: (attachment: NoteAttachment) => void;
}) {
  if (!attachments.length) return null;
  return (
    <aside className="mx-auto mb-5 max-w-4xl overflow-hidden rounded-control border border-subtle bg-surface-sunken">
      <header className="flex items-center gap-2 border-b border-subtle px-3 py-2 text-meta text-secondary">
        <Paperclip size={13} />
        <span className="font-medium">Ek havuzu</span>
        <span className="text-muted">Metinde yer almayan {attachments.length} ek</span>
      </header>
      <ul className="divide-y divide-subtle">
        {attachments.map((attachment) => (
          <li key={attachment.id} className="flex min-w-0 items-center gap-2 px-3 py-2">
            <span className="text-icon">
              <AttachmentIcon attachment={attachment} />
            </span>
            <span className="min-w-0 flex-1 truncate text-meta text-primary">{attachment.name}</span>
            <Button size="sm" variant="ghost" disabled={disabled} onClick={() => onInsert(attachment)}>
              <Plus size={13} /> İmlece ekle
            </Button>
            <IconButton title={`${attachment.name} ekini sil`} disabled={disabled} onClick={() => onRemove(attachment)}>
              <Trash2 size={13} />
            </IconButton>
          </li>
        ))}
      </ul>
    </aside>
  );
}

export function NotesPage() {
  const route = useHashRoute();
  const focusId = route.params.get("focus") ?? "";
  const online = useOnline();
  const [theme] = useTheme();
  const toast = useToast();
  const imageInput = useRef<HTMLInputElement>(null);
  const audioInput = useRef<HTMLInputElement>(null);
  const drawingInput = useRef<HTMLInputElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const editor = useRef<HTMLTextAreaElement>(null);
  const caret = useRef(0);
  const [caretPosition, setCaretPosition] = useState(0);
  const [highlightsOpen, setHighlightsOpen] = useState(route.params.get("highlights") === "1");
  const [mode, setMode] = useState<EditorMode>("write");
  const [selectedId, setSelectedId] = useState(focusId);
  const [creating, setCreating] = useState(route.params.get("new") === "1");
  const [draft, setDraft] = useState(() => (route.params.get("new") === "1" ? starterBody() : ""));
  const [draftFolderId, setDraftFolderId] = useState<string | null>(route.params.get("folder"));
  // Draft'in ait oldugu not. Arka plan refetch'i secili notun YENI nesnesini
  // getirdiginde draft uzerine yazilmaz; yalnizca not id'si degistiginde yuklenir.
  const draftNoteId = useRef<string | null>(null);

  const { data: notes = [] } = useQuery({
    queryKey: ["notes"],
    queryFn: () => api.get<Note[]>("/notes"),
  });
  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });
  const { data: folders = [] } = useQuery({
    queryKey: ["note-folders"],
    queryFn: () => api.get<NoteFolder[]>("/note-folders"),
  });
  const selected = notes.find((note) => note.id === selectedId) ?? null;
  const { data: selectedDetail, isLoading: detailLoading } = useQuery({
    queryKey: ["note", selectedId],
    queryFn: () => api.get<Note>(`/notes/${selectedId}`),
    enabled: Boolean(selectedId && !creating && mode === "canvas"),
  });
  const canvasNote = selectedDetail?.id === selectedId ? selectedDetail : null;
  const projectTitles = useMemo(() => new Map(projects.map((project) => [project.id, project.title])), [projects]);
  const unplacedAttachments = useMemo(
    () => (selected?.attachments ?? []).filter((attachment) => !draft.includes(`(${attachment.url})`)),
    [draft, selected?.attachments],
  );
  const slash = useMemo(() => slashContext(draft, caretPosition), [draft, caretPosition]);

  useEffect(() => {
    if (focusId) {
      setSelectedId(focusId);
      setCreating(false);
      setMode("write");
      setDraftFolderId(notes.find((note) => note.id === focusId)?.folder_id ?? null);
    }
  }, [focusId, notes]);

  useEffect(() => {
    if (creating) return;
    if (selected) {
      if (draftNoteId.current === selected.id) return;
      setDraft(selected.body);
      caret.current = selected.body.length;
      draftNoteId.current = selected.id;
      setMode(selected.default_view === "canvas" ? "canvas" : "write");
      setDraftFolderId(selected.folder_id ?? null);
      return;
    }
    if (!selectedId && notes[0]) {
      setSelectedId(notes[0].id);
      setDraft(notes[0].body);
      caret.current = notes[0].body.length;
      draftNoteId.current = notes[0].id;
      setMode(notes[0].default_view === "canvas" ? "canvas" : "write");
      setDraftFolderId(notes[0].folder_id ?? null);
    }
  }, [creating, notes, selected, selectedId]);

  const save = useMutation({
    mutationFn: () =>
      creating
        ? api.post<Note>("/notes", { body: draft.trim(), folder_id: draftFolderId })
        : api.patch<Note>(`/notes/${selectedId}`, { body: draft.trim() }),
    onSuccess: (note) => {
      setCreating(false);
      setSelectedId(note.id);
      setDraft(note.body);
      setDraftFolderId(note.folder_id ?? null);
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

  const notePreference = useMutation({
    mutationFn: (values: { default_view?: "page" | "canvas"; page_width?: PageWidth }) =>
      api.patch<Note>(`/notes/${selectedId}`, values),
    onSuccess: refreshNotes,
  });

  const moveNote = useMutation({
    mutationFn: (folder_id: string | null) => api.patch<Note>(`/notes/${selectedId}`, { folder_id }),
    onSuccess: (note) => {
      setDraftFolderId(note.folder_id ?? null);
      refreshNotes();
      toast.push("Not taşındı.", { tone: "ok" });
    },
    onError: () => toast.push("Not taşınamadı.", { tone: "danger" }),
  });

  const saveCanvas = useMutation({
    mutationFn: (canvas_state: NonNullable<Note["canvas_state"]>) =>
      api.patch<Note>(`/notes/${selectedId}`, { canvas_state, default_view: "canvas" }),
    onSuccess: refreshNotes,
    onError: () => toast.push("Tuval kaydedilemedi.", { tone: "danger" }),
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
    mutationFn: async ({ files, at, source }: UploadRequest) => {
      if (!selectedId) throw new Error("Önce notu kaydet");
      const uploaded: NoteAttachment[] = [];
      try {
        for (const file of files) {
          uploaded.push(await api.upload<NoteAttachment>(`/notes/${selectedId}/attachments`, file));
        }
        const insertion = insertMarkdownAt(source, at, uploaded.map(attachmentMarkdown).join("\n\n"));
        const note = await api.patch<Note>(`/notes/${selectedId}`, { body: insertion.value.trim() });
        return { uploaded, note, caret: insertion.caret };
      } catch (error) {
        for (const attachment of uploaded) {
          await api.del(`/notes/${selectedId}/attachments/${attachment.id}`).catch(() => undefined);
        }
        throw error;
      }
    },
    onSuccess: ({ uploaded, note, caret: nextCaret }) => {
      setDraft(note.body);
      draftNoteId.current = note.id;
      caret.current = nextCaret;
      refreshNotes();
      toast.push(`${uploaded.length} ek nota yerleştirildi.`, { tone: "ok" });
      requestAnimationFrame(() => {
        editor.current?.focus();
        editor.current?.setSelectionRange(nextCaret, nextCaret);
      });
    },
    onError: (error: Error) => toast.push(error.message || "Ek yüklenemedi.", { tone: "danger" }),
  });

  const removeAttachment = useMutation({
    mutationFn: async (attachment: NoteAttachment) => {
      await api.del(`/notes/${selectedId}/attachments/${attachment.id}`);
      const nextBody = removeAttachmentMarkdown(draft, attachment);
      if (nextBody === draft.trim()) return null;
      return api.patch<Note>(`/notes/${selectedId}`, { body: nextBody });
    },
    onSuccess: (note) => {
      if (note) {
        setDraft(note.body);
        draftNoteId.current = note.id;
      }
      refreshNotes();
      toast.push("Ek silindi.", { tone: "ok" });
    },
  });

  const attachFiles = (files: File[]) => {
    if (!files.length) return;
    upload.mutate({ files, at: caret.current, source: draft });
  };

  const insertInline = (text: string, caretOffset = 0) => {
    const insertion = insertInlineAt(draft, caret.current, text);
    const nextCaret = insertion.caret + caretOffset;
    setDraft(insertion.value);
    caret.current = nextCaret;
    requestAnimationFrame(() => {
      editor.current?.focus();
      editor.current?.setSelectionRange(nextCaret, nextCaret);
    });
  };

  const insertExistingAttachment = (attachment: NoteAttachment) => {
    setMode("write");
    const insertion = insertMarkdownAt(draft, caret.current, attachmentMarkdown(attachment));
    setDraft(insertion.value);
    caret.current = insertion.caret;
    requestAnimationFrame(() => {
      editor.current?.focus();
      editor.current?.setSelectionRange(insertion.caret, insertion.caret);
    });
  };

  const confirmRemoveAttachment = async (attachment: NoteAttachment) => {
    const ok = await confirmDialog({
      title: "Ek silinsin mi?",
      body: `${attachment.name} bu nottan ve Markdown içeriğinden kaldırılacak.`,
      confirmLabel: "Eki Sil",
      tone: "danger",
    });
    if (ok) removeAttachment.mutate(attachment);
  };

  const dirty = creating ? Boolean(draft.trim()) : Boolean(selected && draft !== selected.body);
  useEffect(() => {
    if (!dirty) return;
    const handleExternalNavigation = (rawEvent: Event) => {
      const event = rawEvent as CustomEvent<NavigationRequest>;
      event.preventDefault();
      void confirmDialog({
        title: "Kaydedilmemiş değişiklikler var",
        body: "Bu sayfadan ayrılırsanız mevcut değişiklikler kaybolacak. Yine de devam edilsin mi?",
        confirmLabel: "Değişiklikleri At ve Ayrıl",
        tone: "danger",
      }).then((confirmed) => {
        if (confirmed) navigate(event.detail.href);
      });
    };
    window.addEventListener(BEFORE_NAVIGATION_EVENT, handleExternalNavigation);
    return () => window.removeEventListener(BEFORE_NAVIGATION_EVENT, handleExternalNavigation);
  }, [dirty]);

  const changeMode = (next: EditorMode) => {
    setMode(next);
    if (!creating && selectedId && online) {
      notePreference.mutate({ default_view: next === "canvas" ? "canvas" : "page" });
    }
  };
  const beginNote = async (title?: string, folderId: string | null = null) => {
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
    setDraftFolderId(folderId);
    setMode("write");
    caret.current = starterBody(title).length;
    draftNoteId.current = null;
    navigate(`/notes?new=1${folderId ? `&folder=${folderId}` : ""}`);
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
    setDraftFolderId(note.folder_id ?? null);
    setMode(note.default_view === "canvas" ? "canvas" : "write");
    caret.current = note.body.length;
    draftNoteId.current = note.id;
    navigate(`/notes?focus=${note.id}`);
  };

  useEffect(() => {
    const handleNavigation = (rawEvent: Event) => {
      const event = rawEvent as CustomEvent<NoteNavigationRequest>;
      const request = event.detail;
      event.preventDefault();
      if (request.kind === "new") {
        void beginNote(undefined, request.folderId ?? null);
        return;
      }
      if (request.kind === "highlights") {
        setHighlightsOpen(true);
        navigate("/notes?highlights=1");
        return;
      }
      const note = notes.find((item) => item.id === request.id);
      if (note) void openNote(note);
    };
    window.addEventListener(NOTE_NAVIGATION_EVENT, handleNavigation);
    return () => window.removeEventListener(NOTE_NAVIGATION_EVENT, handleNavigation);
  });

  const chooseSlashCommand = (command: SlashCommand) => {
    if (!slash) return;
    const cleared = `${draft.slice(0, slash.start)}${draft.slice(caretPosition)}`;
    setDraft(cleared);
    caret.current = slash.start;
    setCaretPosition(slash.start);
    if (command.markdown !== undefined) {
      const insertion = insertInlineAt(cleared, slash.start, command.markdown);
      const nextCaret = Math.max(slash.start, insertion.caret + (command.caretOffset ?? 0));
      setDraft(insertion.value);
      caret.current = nextCaret;
      setCaretPosition(nextCaret);
      requestAnimationFrame(() => {
        editor.current?.focus();
        editor.current?.setSelectionRange(nextCaret, nextCaret);
      });
      return;
    }
    requestAnimationFrame(() => {
      if (command.action === "image") imageInput.current?.click();
      if (command.action === "audio") audioInput.current?.click();
      if (command.action === "file") fileInput.current?.click();
      if (command.action === "highlights") setHighlightsOpen(true);
      if (command.action === "new-note") void beginNote();
    });
  };
  const closeHighlights = () => {
    setHighlightsOpen(false);
    if (route.params.get("highlights") === "1") {
      navigate(selectedId ? `/notes?focus=${selectedId}` : "/notes");
    }
  };
  return (
    <PageFrame className="py-3">
      <Surface className="min-h-workspace-body overflow-hidden">
        <main className="min-w-0">
          {!creating && !selected ? (
            <div className="flex min-h-screen items-center justify-center p-6">
              <Empty variant="page" title="Bir not seç">
                Ana menüde Notlar altından bir kayıt aç veya yeni bir düşünce yakala.
                <span className="mt-3 block">
                  <Button variant="primary" onClick={() => beginNote()}>
                    <Plus size={14} /> Yeni not
                  </Button>
                </span>
              </Empty>
            </div>
          ) : (
            <>
              <header className="flex flex-wrap items-center gap-2 border-b border-subtle px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-heading text-primary">{creating ? "Yeni not" : selected?.title}</p>
                  <div className="flex flex-wrap items-center gap-1.5 text-meta text-muted">
                    <span>
                      {dirty
                        ? "Kaydedilmemiş değişiklik"
                        : selected
                          ? `Kaydedildi · ${dateLabel(selected.updated_at)}`
                          : "Yeni notu kaydedince ek ekleyebilirsin"}
                    </span>
                    {selected?.project_id ? (
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 rounded-control text-accent hover:underline"
                        onClick={() => navigate(`/projects?focus=${selected.project_id}`)}
                      >
                        <FolderKanban size={11} /> {projectTitles.get(selected.project_id) ?? "Proje notu"}
                      </button>
                    ) : null}
                  </div>
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
                <Select
                  value={draftFolderId ?? ""}
                  ariaLabel="Not klasörü"
                  disabled={!online || moveNote.isPending || Boolean(selected?.project_id)}
                  className="max-w-44"
                  onChange={(value) => {
                    const folderId = value || null;
                    if (creating) setDraftFolderId(folderId);
                    else moveNote.mutate(folderId);
                  }}
                >
                  <option value="">Kök Notlar</option>
                  {folders.map((folder) => (
                    <option key={folder.id} value={folder.id}>
                      {folder.name}
                    </option>
                  ))}
                </Select>
                <div className="inline-flex rounded-control border border-subtle bg-surface-sunken p-0.5">
                  <Button
                    size="sm"
                    variant="ghost"
                    className={cx("border-0 px-2.5", mode === "write" && "bg-surface shadow-raised")}
                    onClick={() => changeMode("write")}
                  >
                    <Pencil size={14} /> Yaz
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className={cx("border-0 px-2.5", mode === "preview" && "bg-surface shadow-raised")}
                    onClick={() => changeMode("preview")}
                  >
                    <Eye size={14} /> Önizle
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={creating}
                    title={creating ? "Tuvali açmak için önce notu kaydet" : "Tuval"}
                    className={cx("border-0 px-2.5", mode === "canvas" && "bg-surface shadow-raised")}
                    onClick={() => changeMode("canvas")}
                  >
                    <Brush size={14} /> Tuval
                  </Button>
                </div>
                {mode !== "canvas" ? (
                  <Button
                    variant="primary"
                    disabled={!online || !draft.trim() || !dirty || save.isPending}
                    onClick={() => save.mutate()}
                  >
                    <Save size={14} /> {save.isPending ? "Kaydediliyor" : "Kaydet"}
                  </Button>
                ) : (
                  <Chip>{saveCanvas.isPending ? "Tuval kaydediliyor" : "Otomatik kayıt"}</Chip>
                )}
              </header>

              {mode !== "canvas" ? (
                <div className="flex flex-wrap items-center gap-1.5 border-b border-subtle px-4 py-2.5">
                  <FileInput
                    ref={imageInput}
                    accept="image/jpeg,image/png,image/webp,image/gif"
                    multiple
                    onChange={(event) => {
                      attachFiles(Array.from(event.target.files ?? []));
                      event.target.value = "";
                    }}
                  />
                  <FileInput
                    ref={fileInput}
                    multiple
                    accept="application/pdf,text/plain,text/markdown,text/csv,video/mp4,video/webm,video/quicktime,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.odp,.zip"
                    onChange={(event) => {
                      attachFiles(Array.from(event.target.files ?? []));
                      event.target.value = "";
                    }}
                  />
                  <FileInput
                    ref={audioInput}
                    accept="audio/*"
                    multiple
                    onChange={(event) => {
                      attachFiles(Array.from(event.target.files ?? []));
                      event.target.value = "";
                    }}
                  />
                  <FileInput
                    ref={drawingInput}
                    accept=".excalidraw,application/vnd.excalidraw+json"
                    onChange={(event) => {
                      attachFiles(Array.from(event.target.files ?? []));
                      event.target.value = "";
                    }}
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={!online || creating || upload.isPending}
                    title={creating ? "Önce notu kaydet" : "İmleç konumuna görsel ekle"}
                    onClick={() => imageInput.current?.click()}
                  >
                    <FileImage size={14} /> Resim
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={!online || creating || upload.isPending}
                    title={creating ? "Önce notu kaydet" : "İmleç konumuna ses dosyası ekle"}
                    onClick={() => audioInput.current?.click()}
                  >
                    <FileAudio size={14} /> Ses dosyası
                  </Button>
                  <VoiceRecorder
                    disabled={!online || creating || upload.isPending}
                    onFile={(file) => attachFiles([file])}
                    onError={(message) => toast.push(message, { tone: "danger" })}
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={!online || creating || upload.isPending}
                    title={creating ? "Önce notu kaydet" : "İmleç konumuna dosya, PDF veya video ekle"}
                    onClick={() => fileInput.current?.click()}
                  >
                    <FileIcon size={14} /> Dosya
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={!online || creating || upload.isPending}
                    title={creating ? "Önce notu kaydet" : "İmleç konumuna Excalidraw dosyası ekle"}
                    onClick={() => drawingInput.current?.click()}
                  >
                    <FilePenLine size={14} /> Çizim
                  </Button>
                  <span className="mx-1 h-5 w-px bg-subtle" aria-hidden />
                  <Button size="sm" variant="ghost" onClick={() => insertInline("[[]]", -2)}>
                    <Link2 size={14} /> Wikilink
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setHighlightsOpen(true)}>
                    <Highlighter size={14} /> Vurgular
                  </Button>
                  <span className="min-w-2 flex-1" />
                  <Chip>{selected?.attachments?.length ?? 0} ek</Chip>
                  <Kbd>⌘S</Kbd>
                  <div
                    className="ml-1 inline-flex rounded-control border border-subtle bg-surface-sunken p-0.5"
                    aria-label="Sayfa genişliği"
                  >
                    {(["compact", "wide", "full"] as const).map((width) => (
                      <Button
                        key={width}
                        size="sm"
                        variant="ghost"
                        className={cx(
                          "h-7 border-0 px-2",
                          (selected?.page_width ?? "compact") === width && "bg-surface",
                        )}
                        onClick={() => notePreference.mutate({ page_width: width })}
                      >
                        {width === "compact" ? "Dar" : width === "wide" ? "Geniş" : "Tam"}
                      </Button>
                    ))}
                  </div>
                </div>
              ) : null}

              {mode === "write" ? (
                <div
                  className={cx(
                    "relative mx-auto px-5 py-5",
                    (selected?.page_width ?? "compact") === "compact"
                      ? "max-w-4xl"
                      : (selected?.page_width ?? "compact") === "wide"
                        ? "max-w-6xl"
                        : "max-w-none",
                  )}
                >
                  {slash && <SlashCommandMenu query={slash.query} onChoose={chooseSlashCommand} />}
                  <Textarea
                    ref={editor}
                    value={draft}
                    onChange={setDraft}
                    onCaret={(position) => {
                      caret.current = position;
                      setCaretPosition(position);
                    }}
                    ariaLabel="Not içeriği"
                    placeholder="# Başlık\n\nDüşünceni yaz…"
                    onPaste={(event) => {
                      const files = Array.from(event.clipboardData.files);
                      if (!files.length || creating || !online) return;
                      event.preventDefault();
                      attachFiles(files);
                    }}
                    onDragOver={(event) => {
                      if (event.dataTransfer.types.includes("Files")) event.preventDefault();
                    }}
                    onDrop={(event) => {
                      const files = Array.from(event.dataTransfer.files);
                      if (!files.length || creating || !online) return;
                      event.preventDefault();
                      attachFiles(files);
                    }}
                    className="min-h-screen w-full resize-none border-0 bg-transparent p-0 font-mono leading-relaxed focus:border-transparent focus:ring-0"
                    onKeyDown={(event) => {
                      if ((event.metaKey || event.ctrlKey) && event.key.toLocaleLowerCase("tr") === "s") {
                        event.preventDefault();
                        if (online && dirty && draft.trim()) save.mutate();
                        return;
                      }
                      if (event.key === "Escape" && slash) {
                        event.preventDefault();
                        const next = `${draft.slice(0, slash.start)}${draft.slice(caretPosition)}`;
                        setDraft(next);
                        caret.current = slash.start;
                        setCaretPosition(slash.start);
                        return;
                      }
                      if (event.key === "Enter" && slash) {
                        const first = SLASH_COMMANDS.find((command) =>
                          `${command.label} ${command.keywords}`.toLocaleLowerCase("tr").includes(slash.query),
                        );
                        if (first) {
                          event.preventDefault();
                          chooseSlashCommand(first);
                        }
                      }
                    }}
                  />
                </div>
              ) : mode === "preview" ? (
                <article
                  className={cx(
                    "mx-auto min-h-screen px-5 py-5",
                    (selected?.page_width ?? "compact") === "compact"
                      ? "max-w-4xl"
                      : (selected?.page_width ?? "compact") === "wide"
                        ? "max-w-6xl"
                        : "max-w-none",
                  )}
                >
                  <Markdown
                    source={draft}
                    links={selected?.resolved_links ?? []}
                    unresolved={selected?.unresolved_links ?? []}
                    attachments={selected?.attachments ?? []}
                    onRemoveAttachment={confirmRemoveAttachment}
                    onMissingClick={(target) => beginNote(target)}
                    className="article-content"
                  />
                </article>
              ) : detailLoading || !canvasNote ? (
                <div className="flex min-h-[36rem] items-center justify-center text-meta text-muted">
                  Tuval yükleniyor…
                </div>
              ) : (
                <CanvasErrorBoundary key={canvasNote.id}>
                  <Suspense
                    fallback={
                      <div className="flex min-h-[36rem] items-center justify-center text-meta text-muted">
                        Tuval hazırlanıyor…
                      </div>
                    }
                  >
                    <NoteCanvas
                      initialState={canvasNote.canvas_state ?? {}}
                      noteId={canvasNote.id}
                      noteTitle={canvasNote.title}
                      attachments={canvasNote.attachments ?? []}
                      readOnly={!online}
                      theme={resolvedTheme(theme)}
                      onSave={(state) => saveCanvas.mutate(state)}
                    />
                  </Suspense>
                </CanvasErrorBoundary>
              )}

              {mode !== "canvas" ? (
                <AttachmentPool
                  attachments={unplacedAttachments}
                  disabled={!online || removeAttachment.isPending}
                  onInsert={insertExistingAttachment}
                  onRemove={confirmRemoveAttachment}
                />
              ) : null}

              <footer className="flex flex-wrap items-center justify-end gap-3 border-t border-subtle px-4 py-2 text-meta text-muted">
                <span>{draft.trim() ? draft.trim().split(/\s+/).length : 0} kelime</span>
                <span>·</span>
                <span>{draft.length.toLocaleString("tr-TR")} karakter</span>
                <span>·</span>
                <span>{mode === "canvas" ? "Excalidraw tuvali" : "Markdown"}</span>
              </footer>
            </>
          )}
        </main>
      </Surface>

      {!creating && selected && (
        <div className="grid gap-4 xl:grid-cols-2">
          <RelatedPanel entityId={selected.id} />
          <BacklinksPanel entityId={selected.id} />
          {/* Not -> deste bagi varsa "bu notun kartlari" paneli burada cikar. */}
          <NoteFlashcardPanel noteId={selected.id} />
        </div>
      )}
      {highlightsOpen && (
        <BookmarkHighlights
          onClose={closeHighlights}
          onInsert={(markdown) => {
            closeHighlights();
            setMode("write");
            const insertion = insertMarkdownAt(draft, caret.current, markdown);
            setDraft(insertion.value);
            caret.current = insertion.caret;
            setCaretPosition(insertion.caret);
          }}
        />
      )}
    </PageFrame>
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
    <Button size="sm" variant="danger" onClick={stop}>
      <Square size={13} /> Kaydı bitir
    </Button>
  ) : (
    <Button size="sm" variant="ghost" disabled={disabled} onClick={start}>
      <Mic size={14} /> Ses kaydı
    </Button>
  );
}
