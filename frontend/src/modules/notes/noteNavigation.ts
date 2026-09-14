import type { MouseEvent } from "react";

export const NOTE_NAVIGATION_EVENT = "forkos:note-navigation";
export const NOTE_DRAG_MIME = "application/x-forkos-note";
export const NOTE_FOLDER_DRAG_MIME = "application/x-forkos-note-folder";

export type NoteScope = "active" | "archive" | "trash";
export type NoteNavigationRequest =
  | { kind: "new"; folderId?: string | null }
  | { kind: "open"; id: string }
  | { kind: "highlights" }
  | { kind: "journal" }
  | { kind: "scope"; scope: Exclude<NoteScope, "active"> };

export function notesPath(scope: NoteScope = "active"): string {
  return scope === "active" ? "/notes" : `/notes?scope=${scope}`;
}

export function noteListPath(scope: NoteScope): string {
  return scope === "active" ? "/notes" : `/notes?scope=${scope}`;
}

export function requestNoteNavigation(
  event: MouseEvent<HTMLAnchorElement>, request: NoteNavigationRequest,
) {
  const navigation = new CustomEvent<NoteNavigationRequest>(NOTE_NAVIGATION_EVENT, {
    cancelable: true,
    detail: request,
  });
  if (!window.dispatchEvent(navigation)) event.preventDefault();
}
