import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { PomodoroPage } from "./PomodoroPage";
import { PomodoroWidget } from "./PomodoroWidget";

registerModule({ id: "pomodoro", title: "Pomodoro",
  routes: [{ path: "/pomodoro", element: PomodoroPage }], todayWidgets: [PomodoroWidget],
  commands: [{ id: "pomodoro.open", label: "Pomodoro baslat", run: () => navigate("/pomodoro") }],
});
