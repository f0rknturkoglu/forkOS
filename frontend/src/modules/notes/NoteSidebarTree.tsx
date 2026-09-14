import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Folder,
  FolderKanban,
  FolderPlus,
  Highlighter,
  Archive,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react";
import { useHashRoute } from "@/app/router";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import type { Note, NoteFolder, Project } from "@/core/types";
import { Button, IconButton, Input, cx, useToast } from "@/core/ui";
import { formatTrDateTime } from "@/lib/date";
import {
  NOTE_DRAG_MIME,
  NOTE_FOLDER_DRAG_MIME,
  NOTE_NAVIGATION_EVENT,
  type NoteNavigationRequest,
  requestNoteNavigation,
} from "./noteNavigation";

export { NOTE_NAVIGATION_EVENT, type NoteNavigationRequest } from "./noteNavigation";


function noteDate(value: string): string {
  return formatTrDateTime(value, { day: "numeric", month: "short" });
}

function NoteLink({ note, focusId, onNavigate }: { note: Note; focusId: string; onNavigate: () => void }) {
  const active = focusId === note.id;
  return (
    <a
      href={`#/notes?focus=${note.id}`}
      draggable
      onDragStart={(event) => {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData(NOTE_DRAG_MIME, note.id);
      }}
      aria-current={active ? "page" : undefined}
      onClick={(event) => {
        requestNoteNavigation(event, { kind: "open", id: note.id });
        onNavigate();
      }}
      className={cx(
        "group flex min-w-0 items-start gap-2 rounded-control px-2 py-1.5 transition",
        active ? "bg-surface-selected text-primary" : "text-secondary hover:bg-surface-hover hover:text-primary",
      )}
    >
      <FileText size={13} className="mt-0.5 shrink-0 text-icon" />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-meta font-medium">{note.title}</span>
        <span className="block truncate text-micro text-muted">{noteDate(note.updated_at)}</span>
      </span>
    </a>
  );
}

function FolderBranch({
  folder,
  folders,
  notes,
  focusId,
  activeFolderId,
  onNavigate,
  onCreateChild,
  onRename,
  onDelete,
  onMoveNote,
  onMoveFolder,
}: {
  folder: NoteFolder;
  folders: NoteFolder[];
  notes: Note[];
  focusId: string;
  activeFolderId: string;
  onNavigate: () => void;
  onCreateChild: (parentId: string) => void;
  onRename: (folder: NoteFolder) => void;
  onDelete: (folder: NoteFolder) => void;
  onMoveNote: (noteId: string, folderId: string | null) => void;
  onMoveFolder: (folderId: string, parentId: string | null) => void;
}) {
  const nested = folders.filter((item) => item.parent_id === folder.id);
  const folderNotes = notes.filter((note) => note.folder_id === folder.id);
  const containsFocus = folderNotes.some((note) => note.id === focusId);
  const [open, setOpen] = useState(containsFocus || activeFolderId === folder.id);

  return (
    <div className="ml-1 border-l border-subtle pl-1.5">
      <div
        className={cx(
          "group flex min-w-0 items-center rounded-control pr-1 transition",
          activeFolderId === folder.id ? "bg-surface-selected" : "hover:bg-surface-hover",
        )}
        draggable
        onDragStart={(event) => {
          event.dataTransfer.effectAllowed = "move";
          event.dataTransfer.setData(NOTE_FOLDER_DRAG_MIME, folder.id);
        }}
        onDragOver={(event) => {
          if (event.dataTransfer.types.includes(NOTE_DRAG_MIME) || event.dataTransfer.types.includes(NOTE_FOLDER_DRAG_MIME)) event.preventDefault();
        }}
        onDrop={(event) => {
          const noteId = event.dataTransfer.getData(NOTE_DRAG_MIME);
          if (noteId) onMoveNote(noteId, folder.id);
          const folderId = event.dataTransfer.getData(NOTE_FOLDER_DRAG_MIME);
          if (folderId) onMoveFolder(folderId, folder.id);
        }}
      >
        <button
          type="button"
          aria-label={`${folder.name} klasörünü ${open ? "daralt" : "genişlet"}`}
          onClick={() => setOpen((current) => !current)}
          className="flex h-8 min-w-0 flex-1 items-center gap-1.5 px-1.5 text-left text-meta text-secondary"
        >
          {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          <Folder size={13} className="shrink-0 text-icon" />
          <span className="min-w-0 flex-1 truncate">{folder.name}</span>
          <span className="text-micro tabular-nums text-muted">{folder.note_count}</span>
        </button>
        <span className="hidden items-center group-hover:flex group-focus-within:flex">
          <IconButton title={`${folder.name} içine klasör ekle`} onClick={() => onCreateChild(folder.id)}>
            <FolderPlus size={12} />
          </IconButton>
          <IconButton title={`${folder.name} adını değiştir`} onClick={() => onRename(folder)}>
            <Pencil size={12} />
          </IconButton>
          <IconButton title={`${folder.name} klasörünü sil`} tone="danger" onClick={() => onDelete(folder)}>
            <Trash2 size={12} />
          </IconButton>
        </span>
      </div>
      {open && (
        <div className="space-y-0.5 py-0.5">
          {nested.map((child) => (
            <FolderBranch
              key={child.id}
              folder={child}
              folders={folders}
              notes={notes}
              focusId={focusId}
              activeFolderId={activeFolderId}
              onNavigate={onNavigate}
              onCreateChild={onCreateChild}
              onRename={onRename}
              onDelete={onDelete}
              onMoveNote={onMoveNote}
              onMoveFolder={onMoveFolder}
            />
          ))}
          {folderNotes.map((note) => (
            <NoteLink key={note.id} note={note} focusId={focusId} onNavigate={onNavigate} />
          ))}
          <a
            href={`#/notes?new=1&folder=${folder.id}`}
            onClick={(event) => requestNoteNavigation(event, { kind: "new", folderId: folder.id })}
            className="flex h-7 items-center gap-1.5 rounded-control px-2 text-micro text-muted transition hover:bg-surface-hover hover:text-primary"
          >
            <Plus size={11} /> Bu klasöre not
          </a>
        </div>
      )}
    </div>
  );
}

/** Notlar icin ikinci rail yoktur; kasa/agac dogrudan ana sidebar'in altinda yasar. */
export function NoteSidebarTree({ collapsed, onNavigate }: { collapsed: boolean; onNavigate: () => void }) {
  const route = useHashRoute();
  const focusId = route.params.get("focus") ?? "";
  const activeFolderId = route.params.get("folder") ?? "";
  const creating = route.params.get("new") === "1";
  const highlightsActive = route.params.get("highlights") === "1";
  const [folderDraft, setFolderDraft] = useState("");
  const [folderParent, setFolderParent] = useState<string | null | undefined>(undefined);
  const [editing, setEditing] = useState<NoteFolder | null>(null);
  const toast = useToast();
  const { data: notes = [], isLoading } = useQuery({ queryKey: ["notes"], queryFn: () => api.get<Note[]>("/notes") });
  const { data: folders = [] } = useQuery({
    queryKey: ["note-folders"],
    queryFn: () => api.get<NoteFolder[]>("/note-folders"),
  });
  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: () => api.get<Project[]>("/projects") });

  const personal = notes.filter((note) => !note.project_id);
  const unfiled = personal.filter((note) => !note.folder_id);
  const projectNotes = notes.filter((note) => Boolean(note.project_id));
  const roots = folders.filter((folder) => !folder.parent_id);
  const projectTitles = useMemo(() => new Map(projects.map((project) => [project.id, project.title])), [projects]);

  const createFolder = useMutation({
    mutationFn: () => api.post<NoteFolder>("/note-folders", { name: folderDraft.trim(), parent_id: folderParent }),
    onSuccess: () => {
      setFolderDraft("");
      setFolderParent(undefined);
      invalidateAfter("note.write");
      toast.push("Klasör oluşturuldu.", { tone: "ok" });
    },
    onError: () => toast.push("Klasör oluşturulamadı.", { tone: "danger" }),
  });
  const renameFolder = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => api.patch(`/note-folders/${id}`, { name }),
    onSuccess: () => {
      setEditing(null);
      invalidateAfter("note.write");
    },
  });
  const deleteFolder = useMutation({
    mutationFn: (id: string) => api.del(`/note-folders/${id}`),
    onSuccess: () => invalidateAfter("note.write"),
  });
  const moveNote = useMutation({
    mutationFn: ({ noteId, folderId }: { noteId: string; folderId: string | null }) =>
      api.patch(`/notes/${noteId}`, { folder_id: folderId }),
    onSuccess: () => invalidateAfter("note.write"),
  });
  const moveFolder = useMutation({
    mutationFn: ({ folderId, parentId }: { folderId: string; parentId: string | null }) =>
      api.patch(`/note-folders/${folderId}`, { parent_id: parentId }),
    onSuccess: () => invalidateAfter("note.write"),
    onError: () => toast.push("Klasör taşınamadı.", { tone: "danger" }),
  });

  if (collapsed) return null;

  const beginFolder = (parentId: string | null) => {
    setFolderDraft("");
    setFolderParent(parentId);
    setEditing(null);
  };
  const removeFolder = async (folder: NoteFolder) => {
    const ok = await confirmDialog({
      title: "Klasör silinsin mi?",
      body: `“${folder.name}” silinecek; içindeki notlar silinmeden Kök Notlar'a taşınacak.`,
      confirmLabel: "Klasörü Sil",
      tone: "danger",
    });
    if (ok) deleteFolder.mutate(folder.id);
  };

  return (
    <div className="ml-4 mt-1 border-l border-subtle pl-2">
      <div className="flex items-center gap-1">
        <a
          href="#/notes?new=1"
          aria-current={creating && !activeFolderId ? "page" : undefined}
          onClick={(event) => {
            requestNoteNavigation(event, { kind: "new", folderId: null });
            onNavigate();
          }}
          className={cx(
            "flex h-8 min-w-0 flex-1 items-center gap-2 rounded-control px-2 text-meta transition",
            creating && !activeFolderId
              ? "bg-surface-selected text-primary"
              : "text-secondary hover:bg-surface-hover hover:text-primary",
          )}
        >
          <Plus size={13} className="text-icon" /> Yeni not
        </a>
        <IconButton title="Yeni klasör" onClick={() => beginFolder(null)}>
          <FolderPlus size={13} />
        </IconButton>
      </div>
      <a
        href="#/notes?highlights=1"
        aria-current={highlightsActive ? "page" : undefined}
        onClick={(event) => {
          requestNoteNavigation(event, { kind: "highlights" });
          onNavigate();
        }}
        className={cx(
          "mt-0.5 flex h-8 items-center gap-2 rounded-control px-2 text-meta transition",
          highlightsActive
            ? "bg-surface-selected text-primary"
            : "text-secondary hover:bg-surface-hover hover:text-primary",
        )}
      >
        <Highlighter size={13} className="text-icon" /> Vurgular
      </a>
      <a
        href="#/notes?journal=today"
        className="mt-0.5 flex h-8 items-center gap-2 rounded-control px-2 text-meta text-secondary transition hover:bg-surface-hover hover:text-primary"
      >
        <FileText size={13} className="text-icon" /> Bugünün günlüğü
      </a>
      <a
        href="#/notes?scope=archive"
        className="mt-0.5 flex h-8 items-center gap-2 rounded-control px-2 text-meta text-secondary transition hover:bg-surface-hover hover:text-primary"
      >
        <Archive size={13} className="text-icon" /> Arşiv
      </a>
      <a
        href="#/notes?scope=trash"
        className="mt-0.5 flex h-8 items-center gap-2 rounded-control px-2 text-meta text-secondary transition hover:bg-surface-hover hover:text-primary"
      >
        <Trash2 size={13} className="text-icon" /> Çöp kutusu
      </a>

      {folderParent !== undefined && (
        <form
          className="mt-1 flex items-center gap-1"
          onSubmit={(event) => {
            event.preventDefault();
            if (folderDraft.trim()) createFolder.mutate();
          }}
        >
          <Input
            value={folderDraft}
            onChange={setFolderDraft}
            placeholder="Klasör adı"
            autoFocus
            className="h-8 min-w-0 flex-1"
            onKeyDown={(event) => event.key === "Escape" && setFolderParent(undefined)}
          />
          <Button type="submit" size="sm" disabled={!folderDraft.trim() || createFolder.isPending}>
            Ekle
          </Button>
        </form>
      )}

      {editing && (
        <form
          className="mt-1 flex items-center gap-1"
          onSubmit={(event) => {
            event.preventDefault();
            if (folderDraft.trim()) renameFolder.mutate({ id: editing.id, name: folderDraft.trim() });
          }}
        >
          <Input
            value={folderDraft}
            onChange={setFolderDraft}
            placeholder="Klasör adı"
            autoFocus
            className="h-8 min-w-0 flex-1"
            onKeyDown={(event) => event.key === "Escape" && setEditing(null)}
          />
          <Button type="submit" size="sm" disabled={!folderDraft.trim() || renameFolder.isPending}>
            Kaydet
          </Button>
        </form>
      )}

      {isLoading ? (
        <p className="px-2 py-2 text-meta text-muted">Notlar yükleniyor…</p>
      ) : (
        <div className="mt-1 space-y-0.5">
          {roots.map((folder) => (
            <FolderBranch
              key={folder.id}
              folder={folder}
              folders={folders}
              notes={personal}
              focusId={focusId}
              activeFolderId={activeFolderId}
              onNavigate={onNavigate}
              onCreateChild={beginFolder}
              onRename={(item) => {
                setEditing(item);
                setFolderDraft(item.name);
                setFolderParent(undefined);
              }}
              onDelete={(item) => void removeFolder(item)}
              onMoveNote={(noteId, folderId) => moveNote.mutate({ noteId, folderId })}
              onMoveFolder={(folderId, parentId) => moveFolder.mutate({ folderId, parentId })}
            />
          ))}

          <section
            aria-label="Kök Notlar"
            onDragOver={(event) => {
              if (event.dataTransfer.types.includes(NOTE_DRAG_MIME) || event.dataTransfer.types.includes(NOTE_FOLDER_DRAG_MIME)) event.preventDefault();
            }}
            onDrop={(event) => {
              const noteId = event.dataTransfer.getData(NOTE_DRAG_MIME);
              if (noteId) moveNote.mutate({ noteId, folderId: null });
              const folderId = event.dataTransfer.getData(NOTE_FOLDER_DRAG_MIME);
              if (folderId) moveFolder.mutate({ folderId, parentId: null });
            }}
          >
            <div className="mb-1 mt-2 flex items-center gap-2 px-2">
              <span className="label-caps min-w-0 flex-1 truncate text-muted">Kök Notlar</span>
              <span className="text-micro tabular-nums text-muted">{unfiled.length}</span>
            </div>
            {unfiled.map((note) => (
              <NoteLink key={note.id} note={note} focusId={focusId} onNavigate={onNavigate} />
            ))}
          </section>

          <section aria-label="Proje notları">
            <div className="mb-1 mt-2 flex items-center gap-2 px-2">
              <span className="label-caps min-w-0 flex-1 truncate text-muted">Proje notları</span>
              <span className="text-micro tabular-nums text-muted">{projectNotes.length}</span>
            </div>
            {projectNotes.map((note) => (
              <a
                key={note.id}
                href={`#/notes?focus=${note.id}`}
                aria-current={focusId === note.id ? "page" : undefined}
                onClick={(event) => {
                  requestNoteNavigation(event, { kind: "open", id: note.id });
                  onNavigate();
                }}
                className={cx(
                  "flex min-w-0 items-start gap-2 rounded-control px-2 py-1.5 text-meta transition",
                  focusId === note.id
                    ? "bg-surface-selected text-primary"
                    : "text-secondary hover:bg-surface-hover hover:text-primary",
                )}
              >
                <FolderKanban size={13} className="mt-0.5 shrink-0 text-icon" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{note.title}</span>
                  <span className="block truncate text-micro text-muted">
                    {note.project_id ? (projectTitles.get(note.project_id) ?? "Proje") : "Proje"}
                  </span>
                </span>
              </a>
            ))}
          </section>
        </div>
      )}
    </div>
  );
}
