import { lazy } from "react";
import { StickyNote } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";

const NotesPage = lazy(() => import("./NotesPage").then((module) => ({ default: module.NotesPage })));

registerModule({
  id: "notes",
  title: "Notlar",
  icon: StickyNote,
  group: "capture",
  routes: [{ path: "/notes", element: NotesPage }],
  commands: [
    { id: "notes.open", label: "Notları aç — markdown, fotoğraf ve ses", run: () => navigate("/notes") },
    { id: "notes.new", label: "Yeni not oluştur", run: () => navigate("/notes?new=1") },
  ],
});
