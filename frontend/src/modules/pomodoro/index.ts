import { lazy } from "react";
import { Timer } from "lucide-react";
import { registerModule } from "@/core/registry";
import { PomodoroWidget } from "./PomodoroWidget";
import { QuickActionDock } from "./PomodoroDock";
import { openPomodoro } from "./dock";

const PomodoroPage = lazy(() => import("./PomodoroPage").then((module) => ({ default: module.PomodoroPage })));

registerModule({
  id: "pomodoro",
  title: "Odak",
  description: "Odak seanslarını başlat, zamanını incele ve çalışma bahçeni büyüt.",
  icon: Timer,
  routes: [{ path: "/pomodoro", element: PomodoroPage }],
  todayWidgets: [
    {
      id: "pomodoro.widget",
      title: "Odak",
      component: PomodoroWidget,
      region: "secondary",
      order: 30,
      defaultVisible: false,
    },
  ],
  globalSurfaces: [QuickActionDock],
  commands: [{ id: "pomodoro.open", label: "Odak başlat", run: () => openPomodoro() }],
});
