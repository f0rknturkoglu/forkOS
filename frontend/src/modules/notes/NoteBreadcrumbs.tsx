import { ChevronRight } from "lucide-react";
import { navigate } from "@/app/router";
import type { Note, NoteFolder } from "@/core/types";
import { Button } from "@/core/ui";
import type { NoteScope } from "./noteNavigation";

function ancestors(folderId: string | null | undefined, folders: NoteFolder[]) {
  const byId = new Map(folders.map((folder) => [folder.id, folder]));
  const chain: NoteFolder[] = [];
  const seen = new Set<string>();
  let current = folderId ? byId.get(folderId) : undefined;
  while (current && !seen.has(current.id)) {
    seen.add(current.id);
    chain.unshift(current);
    current = current.parent_id ? byId.get(current.parent_id) : undefined;
  }
  return chain;
}

export function NoteBreadcrumbs({
  note,
  folders,
  scope,
  onNavigate,
}: {
  note: Note | null;
  folders: NoteFolder[];
  scope: NoteScope;
  onNavigate?: (href: string) => void;
}) {
  const root = scope === "archive" ? "Arşiv" : scope === "trash" ? "Çöp Kutusu" : "Kasa";
  const chain = scope === "active" ? ancestors(note?.folder_id, folders) : [];
  return (
    <nav aria-label="Not yolu" className="flex min-w-0 items-center gap-1 text-meta text-muted">
      <Button
        size="sm"
        variant="ghost"
        onClick={() => (onNavigate ?? navigate)(scope === "active" ? "/notes" : `/notes?scope=${scope}`)}
      >
        {root} yolu
      </Button>
      {chain.map((folder) => (
        <span key={folder.id} className="flex min-w-0 items-center gap-1">
          <ChevronRight size={12} />
          <Button size="sm" variant="ghost" onClick={() => (onNavigate ?? navigate)(`/notes?folder=${folder.id}`)}>
            {folder.name}
          </Button>
        </span>
      ))}
      {note && (
        <span className="flex min-w-0 items-center gap-1">
          <ChevronRight size={12} />
          <span className="truncate text-secondary">{note.title}</span>
        </span>
      )}
    </nav>
  );
}
