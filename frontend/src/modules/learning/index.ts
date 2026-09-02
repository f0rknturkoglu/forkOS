import { lazy } from "react";
import { GraduationCap } from "lucide-react";
import { LearningWidget } from "./LearningWidget";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";

const LearningPage = lazy(() => import("./LearningPage").then((module) => ({ default: module.LearningPage })));
const GraphPage = lazy(() => import("./GraphPage").then((module) => ({ default: module.GraphPage })));

registerModule({
  id: "learning",
  title: "Öğrenme",
  icon: GraduationCap,
  group: "track",
  // Faz 12: eski study rotasi ayni sayfaya gider (kurlma yok).
  routes: [
    { path: "/learning", element: LearningPage },
    { path: "/study", element: LearningPage },
    { path: "/graph", element: GraphPage, title: "Bilgi grafı" },
  ],
  todayWidgets: [{ id: "learning.widget", title: "Öğrenme", component: LearningWidget, slot: "left", order: 65 }],
  commands: [
    { id: "learning.open", label: "Öğrenmeyi aç — konular, kurslar, kuyruk", run: () => navigate("/learning") },
    { id: "study.open", label: "Çalışma ağacını aç", run: () => navigate("/study") },
    { id: "graph.open", label: "Bilgi grafını aç — notlardaki bağlantı haritası", run: () => navigate("/graph") },
  ],
});
