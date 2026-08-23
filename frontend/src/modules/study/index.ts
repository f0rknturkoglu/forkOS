import { lazy } from "react";
import { BookOpen } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { StudyWidget } from "./StudyWidget";

const StudyPage = lazy(() => import("./StudyPage").then((module) => ({ default: module.StudyPage })));

registerModule({
  id: "study", title: "Çalışma", icon: BookOpen, group: "track",
  routes: [{ path: "/study", element: StudyPage }],
  todayWidgets: [{ component: StudyWidget, zone: "rhythm", slot: "left", order: 60 }],
  commands: [{ id: "study.open", label: "Çalışma ağacını aç", run: () => navigate("/study") }],
});
