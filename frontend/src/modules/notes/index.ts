import { lazy } from "react";
import { StickyNote } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { NoteSidebarTree } from "./NoteSidebarTree";

const NotesPage = lazy(() => import("./NotesPage").then((module) => ({ default: module.NotesPage })));
const GraphPage = lazy(() => import("../learning/GraphPage").then((module) => ({ default: module.GraphPage })));

registerModule({
  id: "notes",
  title: "Notlar",
  icon: StickyNote,
  group: "capture",
  sidebar: NoteSidebarTree,
  routes: [
    { path: "/notes", element: NotesPage },
    { path: "/graph", element: GraphPage, title: "Bilgi grafı", navigation: "child" },
  ],
  commands: [
    { id: "notes.open", label: "Notları aç — markdown, fotoğraf ve ses", run: () => navigate("/notes") },
    { id: "notes.new", label: "Yeni not oluştur", run: () => navigate("/notes?new=1") },
    { id: "graph.open", label: "Bilgi grafını aç — second brain bağlantı haritası", run: () => navigate("/graph") },
  ],
});
