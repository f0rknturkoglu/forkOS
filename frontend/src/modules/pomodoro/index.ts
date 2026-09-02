import { lazy } from "react";
import { Timer } from "lucide-react";
import { registerModule } from "@/core/registry";
import { PomodoroWidget } from "./PomodoroWidget";
import { PomodoroDock } from "./PomodoroDock";
import { openPomodoro } from "./dock";

const PomodoroPage = lazy(() => import("./PomodoroPage").then((module) => ({ default: module.PomodoroPage })));

registerModule({
  id: "pomodoro",
  title: "Pomodoro",
  icon: Timer,
  group: "do",
  hidden: true,
  routes: [{ path: "/pomodoro", element: PomodoroPage }],
  todayWidgets: [
    {
      id: "pomodoro.widget",
      title: "Pomodoro",
      component: PomodoroWidget,
      slot: "left",
      order: 30,
      defaultVisible: false,
    },
  ],
  globalSurfaces: [PomodoroDock],
  commands: [{ id: "pomodoro.open", label: "Pomodoro başlat", run: () => openPomodoro() }],
});
