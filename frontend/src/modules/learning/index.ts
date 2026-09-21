import { lazy } from "react";
import { GraduationCap } from "lucide-react";
import { LearningWidget } from "./LearningWidget";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";

const LearningPage = lazy(() => import("./LearningPage").then((module) => ({ default: module.LearningPage })));

registerModule({
  id: "learning",
  title: "Öğrenme",
  description: "Konu, kurs ve çalışma kuyruğunu yöneterek öğrenmeni ilerlet.",
  icon: GraduationCap,
  // Faz 12: eski study rotasi ayni sayfaya gider (kurlma yok).
  routes: [
    { path: "/learning", element: LearningPage },
    { path: "/study", element: LearningPage, navigation: "hidden" },
  ],
  todayWidgets: [
    {
      id: "learning.widget",
      title: "Öğrenme",
      component: LearningWidget,
      region: "secondary",
      order: 65,
      defaultVisible: false,
    },
  ],
  commands: [
    { id: "learning.open", label: "Öğrenmeyi aç — konular, kurslar, kuyruk", run: () => navigate("/learning") },
    // Tekrar kuyrugu ayri gorunum: dogrudan `?view=review` deep-link'i.
    {
      id: "learning.review",
      label: "Öğrenme: tekrar kuyruğu",
      run: () => navigate("/learning?view=review"),
    },
    { id: "study.open", label: "Çalışma ağacını aç", run: () => navigate("/study") },
  ],
});
