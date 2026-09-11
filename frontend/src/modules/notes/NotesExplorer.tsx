import { useMemo, useState, type MouseEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronRight,
  ChevronsDownUp,
  FilePlus,
  FileText,
  Folder,
  FolderKanban,
  FolderOpen,
  FolderPlus,
  Highlighter,
  PanelLeftClose,
  Pencil,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import type { Bookmark, Note, NoteFolder, Project } from "@/core/types";
import { Button, Chip, IconButton, Input, cx, useToast } from "@/core/ui";
import { formatTrDateTime } from "@/lib/date";

export const NOTE_NAVIGATION_EVENT = "forkos:note-navigation";
export type NoteNavigationRequest =
  { kind: "new"; folderId?: string | null } | { kind: "open"; id: string } | { kind: "highlights" };

function requestNoteNavigation(event: MouseEvent<HTMLAnchorElement>, request: NoteNavigationRequest) {
  const navigation = new CustomEvent<NoteNavigationRequest>(NOTE_NAVIGATION_EVENT, {
    cancelable: true,
    detail: request,
  });
  if (!window.dispatchEvent(navigation)) event.preventDefault();
}

function noteDate(value: string): string {
  return formatTrDateTime(value, { day: "numeric", month: "short" });
}

interface NotesExplorerProps {
  focusId: string;
  onSelectNote?: (noteId: string) => void;
  onNewNote?: (folderId: string | null) => void;
  onOpenHighlights?: () => void;
  onClosePane?: () => void;
}

export function NotesExplorer({
  focusId,
  onSelectNote,
  onNewNote,
  onOpenHighlights,
  onClosePane,
}: NotesExplorerProps) {
  const toast = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  const [inlineParentId, setInlineParentId] = useState<string | null | undefined>(undefined);
  const [folderDraft, setFolderDraft] = useState("");
  const [editingFolder, setEditingFolder] = useState<NoteFolder | null>(null);
  const [allCollapsed, setAllCollapsed] = useState(false);

  const { data: notes = [], isLoading: notesLoading } = useQuery({
    queryKey: ["notes"],
    queryFn: () => api.get<Note[]>("/notes"),
  });
  const { data: folders = [] } = useQuery({
    queryKey: ["note-folders"],
    queryFn: () => api.get<NoteFolder[]>("/note-folders"),
  });
  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });
  const { data: bookmarks = [] } = useQuery({
    queryKey: ["bookmarks", "highlights-count"],
    queryFn: () => api.get<Bookmark[]>("/bookmarks?limit=200"),
  });

  const highlightsCount = useMemo(
    () => bookmarks.filter((b) => Boolean(b.selection?.trim())).length,
    [bookmarks],
  );

  const projectTitles = useMemo(
    () => new Map(projects.map((project) => [project.id, project.title])),
    [projects],
  );

  const createFolder = useMutation({
    mutationFn: () =>
      api.post<NoteFolder>("/note-folders", {
        name: folderDraft.trim(),
        parent_id: inlineParentId ?? null,
      }),
    onSuccess: () => {
      setFolderDraft("");
      setInlineParentId(undefined);
      invalidateAfter("note.write");
      toast.push("Klasör oluşturuldu.", { tone: "ok" });
    },
    onError: () => toast.push("Klasör oluşturulamadı.", { tone: "danger" }),
  });

  const renameFolder = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => api.patch(`/note-folders/${id}`, { name }),
    onSuccess: () => {
      setEditingFolder(null);
      invalidateAfter("note.write");
      toast.push("Klasör adı güncellendi.", { tone: "ok" });
    },
    onError: () => toast.push("Klasör adı değiştirilemedi.", { tone: "danger" }),
  });

  const deleteFolder = useMutation({
    mutationFn: (id: string) => api.del(`/note-folders/${id}`),
    onSuccess: () => {
      invalidateAfter("note.write");
      toast.push("Klasör silindi.", { tone: "ok" });
    },
    onError: () => toast.push("Klasör silinemedi.", { tone: "danger" }),
  });

  const moveNote = useMutation({
    mutationFn: ({ noteId, folderId }: { noteId: string; folderId: string | null }) =>
      api.patch(`/notes/${noteId}`, { folder_id: folderId }),
    onSuccess: () => {
      invalidateAfter("note.write");
      toast.push("Not taşındı.", { tone: "ok" });
    },
    onError: () => toast.push("Not taşınamadı.", { tone: "danger" }),
  });

  const handleRemoveFolder = async (folder: NoteFolder) => {
    const ok = await confirmDialog({
      title: "Klasör silinsin mi?",
      body: `“${folder.name}” silinecek; içindeki notlar silinmeden Kök Notlar'a taşınacak.`,
      confirmLabel: "Klasörü Sil",
      tone: "danger",
    });
    if (ok) deleteFolder.mutate(folder.id);
  };

  const filteredNotes = useMemo(() => {
    if (!searchQuery.trim()) return notes;
    const query = searchQuery.trim().toLocaleLowerCase("tr");
    return notes.filter((n) => n.title.toLocaleLowerCase("tr").includes(query));
  }, [notes, searchQuery]);

  const personal = filteredNotes.filter((note) => !note.project_id);
  const unfiled = personal.filter((note) => !note.folder_id);
  const projectNotes = filteredNotes.filter((note) => Boolean(note.project_id));
  const rootFolders = folders.filter((folder) => !folder.parent_id);

  return (
    <div className="flex h-full flex-col bg-surface select-none">
      {/* Kasa Başlık Çubuğu */}
      <div className="flex items-center justify-between gap-1 border-b border-subtle px-3 py-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <span className="truncate text-meta font-bold uppercase tracking-wider text-primary">Kasa</span>
          <Chip tone="muted">{notes.length}</Chip>
        </div>

        <div className="flex items-center gap-0.5">
          <IconButton
            title="Yeni not oluştur"
            ariaLabel="Yeni not oluştur"
            onClick={() => {
              if (onNewNote) onNewNote(null);
              else {
                const navEvent = new CustomEvent<NoteNavigationRequest>(NOTE_NAVIGATION_EVENT, {
                  detail: { kind: "new", folderId: null },
                });
                window.dispatchEvent(navEvent);
              }
            }}
          >
            <FilePlus size={14} />
          </IconButton>
          <IconButton
            title="Yeni klasör oluştur"
            ariaLabel="Yeni klasör oluştur"
            onClick={() => {
              setInlineParentId(null);
              setFolderDraft("");
              setEditingFolder(null);
            }}
          >
            <FolderPlus size={14} />
          </IconButton>
          <IconButton
            title={allCollapsed ? "Tümünü genişlet" : "Tümünü daralt"}
            ariaLabel={allCollapsed ? "Tümünü genişlet" : "Tümünü daralt"}
            onClick={() => setAllCollapsed((c) => !c)}
          >
            <ChevronsDownUp size={14} />
          </IconButton>
          {onClosePane && (
            <IconButton title="Gezgini kapat" ariaLabel="Gezgini kapat" onClick={onClosePane}>
              <PanelLeftClose size={14} />
            </IconButton>
          )}
        </div>
      </div>

      {/* Arama Input'u */}
      <div className="border-b border-subtle px-2 py-2">
        <div className="relative flex items-center">
          <Search size={13} className="pointer-events-none absolute left-2.5 text-muted" />
          <Input
            value={searchQuery}
            onChange={setSearchQuery}
            placeholder="Notlarda filtrele..."
            ariaLabel="Notlarda ara"
            className="h-7 w-full pl-7 pr-7 text-meta"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="absolute right-2 text-muted hover:text-primary"
              aria-label="Aramayı temizle"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Akıllı Bölümler: Okuma Vurguları */}
      <div className="border-b border-subtle p-1.5 space-y-0.5">
        <button
          type="button"
          onClick={() => {
            if (onOpenHighlights) onOpenHighlights();
            else {
              const navEvent = new CustomEvent<NoteNavigationRequest>(NOTE_NAVIGATION_EVENT, {
                detail: { kind: "highlights" },
              });
              window.dispatchEvent(navEvent);
            }
          }}
          className="flex w-full items-center justify-between gap-2 rounded-control px-2.5 py-1.5 text-left text-meta text-secondary transition hover:bg-surface-hover hover:text-primary"
        >
          <div className="flex items-center gap-2 min-w-0">
            <Highlighter size={13} className="shrink-0 text-accent" />
            <span className="truncate font-medium">Okuma Vurguları</span>
          </div>
          <span className="text-micro tabular-nums text-muted">{highlightsCount}</span>
        </button>
      </div>

      {/* Inline Kök Klasör Oluşturma */}
      {inlineParentId === null && (
        <form
          className="flex items-center gap-1 border-b border-subtle p-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (folderDraft.trim()) createFolder.mutate();
          }}
        >
          <Input
            value={folderDraft}
            onChange={setFolderDraft}
            placeholder="Klasör adı..."
            autoFocus
            ariaLabel="Yeni klasör adı"
            className="h-7 min-w-0 flex-1 text-meta"
            onKeyDown={(e) => e.key === "Escape" && setInlineParentId(undefined)}
          />
          <Button size="sm" type="submit" disabled={!folderDraft.trim() || createFolder.isPending}>
            Ekle
          </Button>
          <IconButton title="İptal" onClick={() => setInlineParentId(undefined)}>
            <X size={13} />
          </IconButton>
        </form>
      )}

      {/* Klasör Adı Düzenleme */}
      {editingFolder && (
        <form
          className="flex items-center gap-1 border-b border-subtle p-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (folderDraft.trim()) renameFolder.mutate({ id: editingFolder.id, name: folderDraft.trim() });
          }}
        >
          <Input
            value={folderDraft}
            onChange={setFolderDraft}
            placeholder="Yeni klasör adı..."
            autoFocus
            ariaLabel="Klasör adını değiştir"
            className="h-7 min-w-0 flex-1 text-meta"
            onKeyDown={(e) => e.key === "Escape" && setEditingFolder(null)}
          />
          <Button size="sm" type="submit" disabled={!folderDraft.trim() || renameFolder.isPending}>
            Kaydet
          </Button>
          <IconButton title="İptal" onClick={() => setEditingFolder(null)}>
            <X size={13} />
          </IconButton>
        </form>
      )}

      {/* Notlar ve Klasörler Ağacı */}
      <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
        {notesLoading ? (
          <p className="px-3 py-3 text-meta text-muted">Kasa yükleniyor…</p>
        ) : (
          <>
            {/* Klasör Hiyerarşisi */}
            {rootFolders.map((folder) => (
              <FolderItem
                key={folder.id}
                folder={folder}
                allFolders={folders}
                notes={personal}
                focusId={focusId}
                allCollapsed={allCollapsed}
                onSelectNote={onSelectNote}
                onNewNote={onNewNote}
                onCreateChild={(parentId) => {
                  setInlineParentId(parentId);
                  setFolderDraft("");
                  setEditingFolder(null);
                }}
                onRename={(target) => {
                  setEditingFolder(target);
                  setFolderDraft(target.name);
                  setInlineParentId(undefined);
                }}
                onDelete={handleRemoveFolder}
                onMoveNote={(noteId, folderId) => moveNote.mutate({ noteId, folderId })}
              />
            ))}

            {/* Kök Notlar (Klasörsüz) */}
            <section
              aria-label="Kök Notlar"
              onDragOver={(e) => {
                if (e.dataTransfer.types.includes("application/x-forkos-note")) e.preventDefault();
              }}
              onDrop={(e) => {
                const noteId = e.dataTransfer.getData("application/x-forkos-note");
                if (noteId) moveNote.mutate({ noteId, folderId: null });
              }}
              className="pt-1"
            >
              <div className="flex items-center justify-between px-2 py-1 text-micro font-semibold uppercase tracking-wider text-muted">
                <span>Kök Notlar</span>
                <span className="tabular-nums">{unfiled.length}</span>
              </div>
              <div className="space-y-0.5">
                {unfiled.map((note) => (
                  <NoteItem
                    key={note.id}
                    note={note}
                    active={focusId === note.id}
                    onSelectNote={onSelectNote}
                  />
                ))}
              </div>
            </section>

            {/* Proje Notları */}
            {projectNotes.length > 0 && (
              <section aria-label="Projeler" className="pt-2">
                <div className="flex items-center justify-between px-2 py-1 text-micro font-semibold uppercase tracking-wider text-muted">
                  <span>Projeler</span>
                  <span className="tabular-nums">{projectNotes.length}</span>
                </div>
                <div className="space-y-0.5">
                  {projectNotes.map((note) => (
                    <a
                      key={note.id}
                      href={`#/notes?focus=${note.id}`}
                      aria-current={focusId === note.id ? "page" : undefined}
                      onClick={(e) => {
                        requestNoteNavigation(e, { kind: "open", id: note.id });
                        onSelectNote?.(note.id);
                      }}
                      className={cx(
                        "group flex min-w-0 items-start gap-2 rounded-control px-2 py-1.5 text-meta transition",
                        focusId === note.id
                          ? "bg-surface-selected text-primary font-medium"
                          : "text-secondary hover:bg-surface-hover hover:text-primary",
                      )}
                    >
                      <FolderKanban size={13} className="mt-0.5 shrink-0 text-icon" />
                      <div className="min-w-0 flex-1">
                        <span className="block truncate">{note.title}</span>
                        <span className="block truncate text-micro text-muted">
                          {note.project_id ? (projectTitles.get(note.project_id) ?? "Proje") : "Proje"}
                        </span>
                      </div>
                    </a>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function FolderItem({
  folder,
  allFolders,
  notes,
  focusId,
  allCollapsed,
  onSelectNote,
  onNewNote,
  onCreateChild,
  onRename,
  onDelete,
  onMoveNote,
}: {
  folder: NoteFolder;
  allFolders: NoteFolder[];
  notes: Note[];
  focusId: string;
  allCollapsed: boolean;
  onSelectNote?: (noteId: string) => void;
  onNewNote?: (folderId: string | null) => void;
  onCreateChild: (parentId: string) => void;
  onRename: (folder: NoteFolder) => void;
  onDelete: (folder: NoteFolder) => void;
  onMoveNote: (noteId: string, folderId: string | null) => void;
}) {
  const childFolders = allFolders.filter((item) => item.parent_id === folder.id);
  const folderNotes = notes.filter((note) => note.folder_id === folder.id);
  const hasFocusedChild = folderNotes.some((note) => note.id === focusId);

  const [open, setOpen] = useState(hasFocusedChild || !allCollapsed);

  return (
    <div className="space-y-0.5">
      <div
        className={cx(
          "group flex min-w-0 items-center rounded-control pr-1 transition hover:bg-surface-hover",
        )}
        onDragOver={(e) => {
          if (e.dataTransfer.types.includes("application/x-forkos-note")) e.preventDefault();
        }}
        onDrop={(e) => {
          const noteId = e.dataTransfer.getData("application/x-forkos-note");
          if (noteId) onMoveNote(noteId, folder.id);
        }}
      >
        <button
          type="button"
          aria-label={`${folder.name} klasörünü ${open ? "daralt" : "genişlet"}`}
          onClick={() => setOpen((c) => !c)}
          className="flex h-7 min-w-0 flex-1 items-center gap-1.5 px-1.5 text-left text-meta text-secondary"
        >
          {open ? <ChevronDown size={12} className="shrink-0" /> : <ChevronRight size={12} className="shrink-0" />}
          {open ? (
            <FolderOpen size={13} className="shrink-0 text-icon" />
          ) : (
            <Folder size={13} className="shrink-0 text-icon" />
          )}
          <span className="min-w-0 flex-1 truncate font-medium">{folder.name}</span>
          <span className="text-micro tabular-nums text-muted">{folderNotes.length}</span>
        </button>

        <span className="hidden items-center group-hover:flex group-focus-within:flex gap-0.5">
          <IconButton
            title={`${folder.name} içine not ekle`}
            ariaLabel={`${folder.name} içine not ekle`}
            onClick={() => {
              if (onNewNote) onNewNote(folder.id);
              else {
                const navEvent = new CustomEvent<NoteNavigationRequest>(NOTE_NAVIGATION_EVENT, {
                  detail: { kind: "new", folderId: folder.id },
                });
                window.dispatchEvent(navEvent);
              }
            }}
          >
            <Plus size={12} />
          </IconButton>
          <IconButton
            title={`${folder.name} içine alt klasör ekle`}
            ariaLabel={`${folder.name} içine alt klasör ekle`}
            onClick={() => onCreateChild(folder.id)}
          >
            <FolderPlus size={12} />
          </IconButton>
          <IconButton
            title={`${folder.name} adını değiştir`}
            ariaLabel={`${folder.name} adını değiştir`}
            onClick={() => onRename(folder)}
          >
            <Pencil size={12} />
          </IconButton>
          <IconButton
            title={`${folder.name} klasörünü sil`}
            ariaLabel={`${folder.name} klasörünü sil`}
            onClick={() => onDelete(folder)}
          >
            <Trash2 size={12} />
          </IconButton>
        </span>
      </div>

      {open && (
        <div className="ml-3 border-l border-subtle pl-1.5 space-y-0.5">
          {childFolders.map((child) => (
            <FolderItem
              key={child.id}
              folder={child}
              allFolders={allFolders}
              notes={notes}
              focusId={focusId}
              allCollapsed={allCollapsed}
              onSelectNote={onSelectNote}
              onNewNote={onNewNote}
              onCreateChild={onCreateChild}
              onRename={onRename}
              onDelete={onDelete}
              onMoveNote={onMoveNote}
            />
          ))}

          {folderNotes.map((note) => (
            <NoteItem
              key={note.id}
              note={note}
              active={focusId === note.id}
              onSelectNote={onSelectNote}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function NoteItem({
  note,
  active,
  onSelectNote,
}: {
  note: Note;
  active: boolean;
  onSelectNote?: (noteId: string) => void;
}) {
  return (
    <a
      href={`#/notes?focus=${note.id}`}
      draggable
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("application/x-forkos-note", note.id);
      }}
      aria-current={active ? "page" : undefined}
      onClick={(e) => {
        requestNoteNavigation(e, { kind: "open", id: note.id });
        onSelectNote?.(note.id);
      }}
      className={cx(
        "group flex min-w-0 items-start gap-2 rounded-control px-2 py-1.5 transition",
        active
          ? "bg-surface-selected text-primary font-medium shadow-xs"
          : "text-secondary hover:bg-surface-hover hover:text-primary",
      )}
    >
      <FileText size={13} className="mt-0.5 shrink-0 text-icon" />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-meta">{note.title}</span>
        <span className="block truncate text-micro text-muted">{noteDate(note.updated_at)}</span>
      </span>
    </a>
  );
}
