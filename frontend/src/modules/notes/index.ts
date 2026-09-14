import { lazy } from "react";
import { Share2, StickyNote } from "lucide-react";
import { navigate } from "@/app/router";
import { todayKey } from "@/lib/date";
import { registerModule } from "@/core/registry";

const NotesPage = lazy(() => import("./NotesPage").then((module) => ({ default: module.NotesPage })));
const GraphPage = lazy(() => import("../learning/GraphPage").then((module) => ({ default: module.GraphPage })));

registerModule({
  id: "notes",
  title: "Notlar",
  description: "Markdown notlarını yaz, fotoğraf ve sesle zenginleştir, graf kur.",
  icon: StickyNote,
  group: "capture",
  routes: [
    { path: "/notes", element: NotesPage },
    { path: "/graph", element: GraphPage, title: "Bilgi grafı", icon: Share2, navigation: "child" },
  ],
  commands: [
    { id: "notes.open", label: "Notları aç — markdown, fotoğraf ve ses", run: () => navigate("/notes") },
    { id: "notes.new", label: "Yeni not oluştur", run: () => navigate("/notes?new=1") },
    { id: "notes.daily", label: "Bugünün günlüğünü aç", run: () => navigate(`/notes?journal=${todayKey()}`) },
    { id: "graph.open", label: "Bilgi grafını aç — second brain bağlantı haritası", run: () => navigate("/graph") },
  ],
});
