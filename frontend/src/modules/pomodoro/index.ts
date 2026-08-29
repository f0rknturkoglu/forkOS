import { lazy } from "react";
import { Timer } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { PomodoroWidget } from "./PomodoroWidget";

const PomodoroPage = lazy(() => import("./PomodoroPage").then((module) => ({ default: module.PomodoroPage })));

registerModule({
  id: "pomodoro",
  title: "Pomodoro",
  icon: Timer,
  group: "do",
  routes: [{ path: "/pomodoro", element: PomodoroPage }],
  todayWidgets: [{ id: "pomodoro.widget", title: "Pomodoro", component: PomodoroWidget, slot: "left", order: 30 }],
  commands: [{ id: "pomodoro.open", label: "Pomodoro başlat", run: () => navigate("/pomodoro") }],
});
