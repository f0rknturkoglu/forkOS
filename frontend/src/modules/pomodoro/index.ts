import { Timer } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { PomodoroPage } from "./PomodoroPage";
import { PomodoroWidget } from "./PomodoroWidget";

registerModule({ id: "pomodoro", title: "Pomodoro", icon: Timer, group: "do",
  routes: [{ path: "/pomodoro", element: PomodoroPage }], todayWidgets: [{ component: PomodoroWidget, zone: "now", slot: "left", order: 30 }],
  commands: [{ id: "pomodoro.open", label: "Pomodoro başlat", run: () => navigate("/pomodoro") }],
});
