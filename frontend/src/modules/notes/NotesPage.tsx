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
  Network,
  PanelLeftOpen,
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
import type { Entity, Note, NoteAttachment, NoteFolder, Project } from "@/core/types";
import { qs } from "@/core/api";
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
import { useDebounced, useOnline } from "@/lib/hooks";
import { formatTrDateTime, todayKey } from "@/lib/date";
import { CanvasErrorBoundary } from "./CanvasErrorBoundary";
import { BookmarkHighlights } from "./BookmarkHighlights";
import { NotesExplorer } from "./NotesExplorer";
import { NoteBreadcrumbs } from "./NoteBreadcrumbs";
import { NOTE_NAVIGATION_EVENT, type NoteNavigationRequest } from "./noteNavigation";
import { noteListPath, type NoteScope } from "./noteNavigation";
import { SLASH_COMMANDS, SlashCommandMenu, slashContext, type SlashCommand } from "./SlashCommandMenu";
import { completeWikilink, openWikilinkQuery } from "@/core/wikilinks";

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
  const isNewRoute = route.params.get("new") === "1";
  const routeFolderId = route.params.get("folder");
  const routeScope: NoteScope =
    route.params.get("scope") === "archive" ? "archive" : route.params.get("scope") === "trash" ? "trash" : "active";
  const journalDay = route.params.get("journal") === "today" ? todayKey() : route.params.get("journal");
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
  const [explorerOpen, setExplorerOpen] = useState(() => {
    try {
      return localStorage.getItem("lifeos.notesExplorerOpen") !== "false";
    } catch {
      return true;
    }
  });
  const [mode, setMode] = useState<EditorMode>("write");
  const [selectedId, setSelectedId] = useState(focusId);
  const [creating, setCreating] = useState(isNewRoute);
  const isReadOnly = !online || routeScope !== "active";
  const [draft, setDraft] = useState(() => (route.params.get("new") === "1" ? starterBody() : ""));
  const [draftFolderId, setDraftFolderId] = useState<string | null>(route.params.get("folder"));
  // Draft'in ait oldugu not. Arka plan refetch'i secili notun YENI nesnesini
  // getirdiginde draft uzerine yazilmaz; yalnizca not id'si degistiginde yuklenir.
  const draftNoteId = useRef<string | null>(null);
  const draftRevision = useRef(0);
  const failedAutoRevision = useRef<number | null>(null);

  const { data: notes = [] } = useQuery({
    queryKey: ["notes", routeScope],
    queryFn: () => api.get<Note[]>(noteListPath(routeScope)),
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
  const selectedFolder = folders.find((folder) => folder.id === routeFolderId) ?? null;
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
  const wikilinkQuery = openWikilinkQuery(draft, caretPosition);
  const debouncedWikilink = useDebounced(wikilinkQuery ?? "", 150);
  const { data: wikilinkCandidates = [] } = useQuery({
    queryKey: ["search", "wikilink", debouncedWikilink],
    enabled: wikilinkQuery !== null && debouncedWikilink.trim().length > 0,
    queryFn: () => api.get<Entity[]>(`/search${qs({ q: debouncedWikilink, limit: 6 })}`),
  });

  useEffect(() => {
    if (!journalDay || !online) return;
    let active = true;
    void api
      .post<Note>(`/notes/daily/${journalDay}`)
      .then((note) => {
        if (active) navigate(`/notes?focus=${note.id}`);
      })
      .catch(() => {
        if (active) toast.push("Günlük not açılamadı.", { tone: "danger" });
      });
    return () => {
      active = false;
    };
  }, [journalDay, online, toast]);

  useEffect(() => {
    if (routeScope !== "active" && !creating) setMode("preview");
  }, [creating, routeScope]);

  useEffect(() => {
    if (focusId) {
      setSelectedId(focusId);
      setCreating(false);
      setMode("write");
      setDraftFolderId(notes.find((note) => note.id === focusId)?.folder_id ?? null);
    }
  }, [focusId, notes]);

  useEffect(() => {
    // Bir breadcrumb/klasor URL'si not odagi tasimaz. Eski secim yerine o
    // klasorun ilk notunu (veya bos-klasor durumunu) kullanmak icin secimi
    // route degisiminde sifirla.
    if (routeFolderId && !focusId && !isNewRoute) {
      setSelectedId("");
      setCreating(false);
      draftNoteId.current = null;
    }
  }, [focusId, isNewRoute, routeFolderId]);

  useEffect(() => {
    // Arşiv/Çöp/Kasa arasında URL odaksız değiştiğinde, önceki görünümün
    // seçili kimliği yeni scope'ta geçersiz kalabilir. Yeni listenin ilk
    // uygun notu aşağıdaki yükleme etkisi tarafından seçilir.
    if (!focusId && !isNewRoute) {
      setSelectedId("");
      draftNoteId.current = null;
    }
  }, [focusId, isNewRoute, routeScope]);

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
    if (!selectedId) {
      const initial = routeFolderId ? notes.find((note) => note.folder_id === routeFolderId) : notes[0];
      if (!initial) return;
      setSelectedId(initial.id);
      setDraft(initial.body);
      caret.current = initial.body.length;
      draftNoteId.current = initial.id;
      setMode(initial.default_view === "canvas" ? "canvas" : "write");
      setDraftFolderId(initial.folder_id ?? null);
    }
  }, [creating, notes, routeFolderId, selected, selectedId]);

  const save = useMutation({
    mutationFn: ({
      quiet = false,
      body,
      revision,
      noteId,
      folderId,
    }: {
      quiet?: boolean;
      body: string;
      revision: number;
      noteId: string | null;
      folderId: string | null;
    }) =>
      noteId ? api.patch<Note>(`/notes/${noteId}`, { body }) : api.post<Note>("/notes", { body, folder_id: folderId }),
    onSuccess: (note, { quiet, body, revision, noteId }) => {
      setCreating(false);
      setSelectedId(note.id);
      // Otomatik kayit yaniti donene kadar yeni karakter girilmis olabilir.
      // Eski yanit bu yeni taslagi ezmemeli.
      if (draftRevision.current === revision) setDraft(note.body);
      setDraftFolderId(note.folder_id ?? null);
      draftNoteId.current = note.id;
      refreshNotes();
      // Ilk otomatik create dahil her basarili yazma canonical odaga tasinir.
      // Aksi halde ?new=1 route effect'leri secimi tekrar sifirlayabilir.
      if (!noteId || !quiet) navigate(`/notes?focus=${note.id}`);
      if (!quiet) toast.push("Not kaydedildi.", { tone: "ok" });
    },
    onError: (_error, request) => {
      if (request.quiet) failedAutoRevision.current = request.revision;
      toast.push("Not kaydedilemedi.", { tone: "danger" });
    },
  });

  const requestSave = (quiet: boolean) => {
    if (save.isPending || isReadOnly || !draft.trim()) return;
    save.mutate({
      quiet,
      body: draft.trim(),
      revision: draftRevision.current,
      noteId: creating ? null : selectedId || null,
      folderId: draftFolderId,
    });
  };

  useEffect(() => {
    const changed = creating ? Boolean(draft.trim()) : Boolean(selected && draft !== selected.body);
    const revision = draftRevision.current;
    if (!online || isReadOnly || !changed || save.isPending || failedAutoRevision.current === revision) return;
    const timer = window.setTimeout(() => requestSave(true), 800);
    return () => window.clearTimeout(timer);
  }, [creating, draft, draftFolderId, isReadOnly, save, selected, selectedId]);

  const patch = useMutation({
    mutationFn: ({ id, pinned }: { id: string; pinned: boolean }) => api.patch<Note>(`/notes/${id}`, { pinned }),
    onSuccess: refreshNotes,
  });

  const notePreference = useMutation({
    mutationFn: (values: { default_view?: "page" | "canvas" }) => api.patch<Note>(`/notes/${selectedId}`, values),
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
      navigate(noteListPath(routeScope));
      toast.push("Not arşivlendi.", { tone: "ok" });
    },
  });
  const trash = useMutation({
    mutationFn: (id: string) => api.del(`/notes/${id}`),
    onSuccess: () => {
      setSelectedId("");
      refreshNotes();
      navigate("/notes?scope=trash");
      toast.push("Not çöp kutusuna taşındı.", { tone: "ok" });
    },
  });
  const restore = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/notes/${id}/restore`);
      return api.get<Note>(`/notes/${id}`);
    },
    onSuccess: (note) => {
      refreshNotes();
      navigate(note.archived_at ? `/notes?scope=archive&focus=${note.id}` : `/notes?focus=${note.id}`);
      toast.push("Not geri yüklendi.", { tone: "ok" });
    },
  });
  const unarchive = useMutation({
    mutationFn: (id: string) => api.post(`/notes/${id}/unarchive`),
    onSuccess: () => {
      refreshNotes();
      navigate("/notes");
      toast.push("Not arşivden geri yüklendi.", { tone: "ok" });
    },
  });
  const permanentlyDelete = useMutation({
    mutationFn: (id: string) => api.del(`/notes/${id}/permanent`),
    onSuccess: () => {
      setSelectedId("");
      refreshNotes();
      navigate("/notes?scope=trash");
      toast.push("Not kalıcı olarak silindi.", { tone: "ok" });
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

  const updateDraft = (value: string) => {
    draftRevision.current += 1;
    failedAutoRevision.current = null;
    setDraft(value);
  };

  const insertInline = (text: string, caretOffset = 0) => {
    const insertion = insertInlineAt(draft, caret.current, text);
    const nextCaret = insertion.caret + caretOffset;
    updateDraft(insertion.value);
    caret.current = nextCaret;
    requestAnimationFrame(() => {
      editor.current?.focus();
      editor.current?.setSelectionRange(nextCaret, nextCaret);
    });
  };

  const insertWikilink = (title: string) => {
    const insertion = completeWikilink(draft, caret.current, title);
    updateDraft(insertion.value);
    caret.current = insertion.caret;
    setCaretPosition(insertion.caret);
    requestAnimationFrame(() => {
      editor.current?.focus();
      editor.current?.setSelectionRange(insertion.caret, insertion.caret);
    });
  };

  const toggleTask = (line: number, checked: boolean) => {
    const lines = draft.split("\n");
    const current = lines[line];
    if (!current || !/^[-*+]\s+\[[ xX]\]\s+/.test(current)) return;
    lines[line] = current.replace(/^([-*+]\s+)\[[ xX]\]/, `$1[${checked ? "x" : " "}]`);
    updateDraft(lines.join("\n"));
  };

  const insertExistingAttachment = (attachment: NoteAttachment) => {
    setMode("write");
    const insertion = insertMarkdownAt(draft, caret.current, attachmentMarkdown(attachment));
    updateDraft(insertion.value);
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
  const confirmDiscardDraft = async () => {
    if (!dirty) return true;
    return confirmDialog({
      title: "Kaydedilmemiş değişiklikler var",
      body: "Bu sayfadan ayrılırsanız mevcut değişiklikler kaybolacak. Yine de devam edilsin mi?",
      confirmLabel: "Değişiklikleri At ve Ayrıl",
      tone: "danger",
    });
  };
  const navigateWithDraftGuard = async (href: string) => {
    if (await confirmDiscardDraft()) navigate(href);
  };
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

  useEffect(() => {
    if (!dirty) return;
    const guardSmartLocation = (event: MouseEvent) => {
      const anchor = (event.target as Element | null)?.closest<HTMLAnchorElement>(
        'a[href^="#/notes?scope="], a[href="#/notes?journal=today"]',
      );
      if (!anchor) return;
      event.preventDefault();
      event.stopPropagation();
      void navigateWithDraftGuard(anchor.getAttribute("href")?.slice(1) ?? "/notes");
    };
    window.addEventListener("click", guardSmartLocation, true);
    return () => window.removeEventListener("click", guardSmartLocation, true);
  }, [dirty]);

  const changeMode = (next: EditorMode) => {
    if (isReadOnly && next !== "preview") return;
    setMode(next);
    if (!creating && selectedId && !isReadOnly) {
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
      if (request.kind !== "open") return;
      const note = notes.find((item) => item.id === request.id);
      if (note) void openNote(note);
    };
    window.addEventListener(NOTE_NAVIGATION_EVENT, handleNavigation);
    return () => window.removeEventListener(NOTE_NAVIGATION_EVENT, handleNavigation);
  });

  const chooseSlashCommand = (command: SlashCommand) => {
    if (!slash) return;
    const cleared = `${draft.slice(0, slash.start)}${draft.slice(caretPosition)}`;
    updateDraft(cleared);
    caret.current = slash.start;
    setCaretPosition(slash.start);
    if (command.markdown !== undefined) {
      const insertion = insertInlineAt(cleared, slash.start, command.markdown);
      const nextCaret = Math.max(slash.start, insertion.caret + (command.caretOffset ?? 0));
      updateDraft(insertion.value);
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
      <div className="flex items-stretch gap-3 min-h-workspace-body">
        {explorerOpen && routeScope === "active" && (
          <aside
            aria-label="Kasa Gezgini"
            className="w-72 shrink-0 overflow-hidden rounded-control border border-subtle bg-surface flex flex-col"
          >
            <NotesExplorer
              focusId={selectedId}
              onSelectNote={(id) => {
                const note = notes.find((item) => item.id === id);
                if (note) void openNote(note);
              }}
              onNewNote={(folderId) => void beginNote(undefined, folderId)}
              onOpenHighlights={() => {
                setHighlightsOpen(true);
                navigate("/notes?highlights=1");
              }}
              onClosePane={() => {
                setExplorerOpen(false);
                try {
                  localStorage.setItem("lifeos.notesExplorerOpen", "false");
                } catch {}
              }}
            />
          </aside>
        )}

        <Surface className="min-w-0 flex-1 overflow-hidden flex flex-col">
          <main className="min-w-0 flex-1 flex flex-col">
            {!creating && !selected ? (
              <div className="flex min-h-[65vh] flex-1 flex-col items-center justify-center p-6 text-center">
                {!explorerOpen && (
                  <Button
                    size="sm"
                    variant="secondary"
                    className="mb-4"
                    onClick={() => {
                      setExplorerOpen(true);
                      try {
                        localStorage.setItem("lifeos.notesExplorerOpen", "true");
                      } catch {}
                    }}
                  >
                    <PanelLeftOpen size={14} /> Kasa Gezginini Aç
                  </Button>
                )}
                <Empty variant="page" title={selectedFolder ? `“${selectedFolder.name}” boş` : "Bir not seç"}>
                  {selectedFolder
                    ? "Bu klasörde henüz not yok. İlk düşünceyi burada yakala."
                    : "Kasa gezgininden bir not aç veya yeni bir düşünce yakala."}
                  <span className="mt-3 block">
                    <Button
                      variant="primary"
                      disabled={routeScope !== "active"}
                      onClick={() => beginNote(undefined, routeFolderId)}
                    >
                      <Plus size={14} /> Yeni not
                    </Button>
                  </span>
                </Empty>
              </div>
            ) : (
              <>
                <header className="flex flex-wrap items-center gap-2 border-b border-subtle px-4 py-3">
                  {!explorerOpen && (
                    <IconButton
                      title="Kasa gezginini aç"
                      onClick={() => {
                        setExplorerOpen(true);
                        try {
                          localStorage.setItem("lifeos.notesExplorerOpen", "true");
                        } catch {}
                      }}
                    >
                      <PanelLeftOpen size={15} />
                    </IconButton>
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-heading text-primary">{creating ? "Yeni not" : selected?.title}</p>
                    {!creating && (
                      <NoteBreadcrumbs
                        note={selected}
                        folders={folders}
                        scope={routeScope}
                        onNavigate={(href) => void navigateWithDraftGuard(href)}
                      />
                    )}
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
                      {routeScope === "active" && (
                        <>
                          <IconButton
                            title={selected.pinned ? "Sabitlemeyi kaldır" : "Sabitle"}
                            disabled={!online}
                            onClick={() => patch.mutate({ id: selected.id, pinned: !selected.pinned })}
                          >
                            {selected.pinned ? <PinOff size={14} /> : <Pin size={14} />}
                          </IconButton>
                          <IconButton
                            title="Arşivle"
                            disabled={!online}
                            onClick={() => void confirmDiscardDraft().then((ok) => ok && archive.mutate(selected.id))}
                          >
                            <Archive size={14} />
                          </IconButton>
                          <IconButton
                            title="Çöp kutusuna taşı"
                            disabled={!online}
                            onClick={() => void confirmDiscardDraft().then((ok) => ok && trash.mutate(selected.id))}
                          >
                            <Trash2 size={14} />
                          </IconButton>
                        </>
                      )}
                      {routeScope === "archive" && (
                        <>
                          <IconButton
                            title="Arşivden geri yükle"
                            disabled={!online}
                            onClick={() => unarchive.mutate(selected.id)}
                          >
                            <Archive size={14} />
                          </IconButton>
                          <IconButton
                            title="Çöp kutusuna taşı"
                            disabled={!online}
                            onClick={() => void confirmDiscardDraft().then((ok) => ok && trash.mutate(selected.id))}
                          >
                            <Trash2 size={14} />
                          </IconButton>
                        </>
                      )}
                      {routeScope === "trash" && (
                        <>
                          <IconButton title="Geri yükle" disabled={!online} onClick={() => restore.mutate(selected.id)}>
                            <Archive size={14} />
                          </IconButton>
                          <IconButton
                            title="Kalıcı sil"
                            disabled={!online}
                            onClick={async () => {
                              if (
                                await confirmDialog({
                                  title: "Not kalıcı olarak silinsin mi?",
                                  body: "Bu işlem geri alınamaz.",
                                  confirmLabel: "Kalıcı Sil",
                                  tone: "danger",
                                })
                              )
                                permanentlyDelete.mutate(selected.id);
                            }}
                          >
                            <Trash2 size={14} />
                          </IconButton>
                        </>
                      )}
                    </>
                  )}
                  <Select
                    value={draftFolderId ?? ""}
                    ariaLabel="Not klasörü"
                    disabled={isReadOnly || moveNote.isPending || Boolean(selected?.project_id)}
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
                      disabled={isReadOnly}
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
                      disabled={creating || isReadOnly}
                      title={creating ? "Tuvali açmak için önce notu kaydet" : "Tuval"}
                      className={cx("border-0 px-2.5", mode === "canvas" && "bg-surface shadow-raised")}
                      onClick={() => changeMode("canvas")}
                    >
                      <Brush size={14} /> Tuval
                    </Button>
                  </div>
                  {!creating && selected && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => void navigateWithDraftGuard(`/graph?focus=${selected.id}&from=notes`)}
                    >
                      <Network size={14} /> Graf
                    </Button>
                  )}
                  {routeScope === "active" && (
                    <Button size="sm" variant="ghost" onClick={() => void navigateWithDraftGuard("/graph?from=notes")}>
                      <Network size={14} /> Tüm graf
                    </Button>
                  )}
                  {mode !== "canvas" ? (
                    <Button
                      variant="primary"
                      disabled={isReadOnly || !draft.trim() || !dirty || save.isPending}
                      onClick={() => requestSave(false)}
                    >
                      <Save size={14} /> {save.isPending ? "Kaydediliyor" : "Kaydet"}
                    </Button>
                  ) : (
                    <Chip>{saveCanvas.isPending ? "Tuval kaydediliyor" : "Otomatik kayıt"}</Chip>
                  )}
                </header>

                {mode !== "canvas" && !isReadOnly ? (
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
                  </div>
                ) : null}

                {mode === "write" ? (
                  <div className="relative flex flex-1 flex-col px-6 py-6">
                    {slash && <SlashCommandMenu query={slash.query} onChoose={chooseSlashCommand} />}
                    <Textarea
                      ref={editor}
                      value={draft}
                      onChange={updateDraft}
                      disabled={isReadOnly}
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
                          if (dirty && draft.trim()) requestSave(false);
                          return;
                        }
                        if (event.key === "Escape" && wikilinkQuery !== null) {
                          event.preventDefault();
                          const start = draft.slice(0, caretPosition).lastIndexOf("[[");
                          const next = `${draft.slice(0, start)}${draft.slice(caretPosition)}`;
                          updateDraft(next);
                          caret.current = start;
                          setCaretPosition(start);
                          return;
                        }
                        if (event.key === "Escape" && slash) {
                          event.preventDefault();
                          const next = `${draft.slice(0, slash.start)}${draft.slice(caretPosition)}`;
                          updateDraft(next);
                          caret.current = slash.start;
                          setCaretPosition(slash.start);
                          return;
                        }
                        if (event.key === "Enter" && wikilinkQuery !== null && wikilinkCandidates[0]) {
                          event.preventDefault();
                          insertWikilink(wikilinkCandidates[0].title);
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
                    {wikilinkQuery !== null && wikilinkCandidates.length > 0 && (
                      <div className="absolute inset-x-5 bottom-7 z-popover overflow-hidden rounded-overlay border border-subtle bg-surface shadow-overlay">
                        {wikilinkCandidates.map((candidate) => (
                          <Button
                            key={candidate.id}
                            size="sm"
                            variant="ghost"
                            className="flex w-full justify-start gap-2 rounded-none px-3 py-2 text-left"
                            onClick={() => insertWikilink(candidate.title)}
                          >
                            <span className="min-w-0 flex-1 truncate">{candidate.title}</span>
                            <Chip size="xs">{candidate.type}</Chip>
                          </Button>
                        ))}
                      </div>
                    )}
                  </div>
                ) : mode === "preview" ? (
                  <article className="min-h-[70dvh] px-6 py-6">
                    <Markdown
                      source={draft}
                      links={selected?.resolved_links ?? []}
                      unresolved={selected?.unresolved_links ?? []}
                      attachments={selected?.attachments ?? []}
                      onMissingClick={(target) => beginNote(target)}
                      onRemoveAttachment={isReadOnly ? undefined : confirmRemoveAttachment}
                      onTaskToggle={!isReadOnly ? toggleTask : undefined}
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
                        readOnly={isReadOnly}
                        theme={resolvedTheme(theme)}
                        onSave={(state) => saveCanvas.mutate(state)}
                      />
                    </Suspense>
                  </CanvasErrorBoundary>
                )}

                {mode !== "canvas" && !isReadOnly ? (
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
      </div>

      {!creating && selected && (
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
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
            updateDraft(insertion.value);
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
