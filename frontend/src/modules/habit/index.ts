import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { HabitPage } from "./HabitPage";
import { HabitWidget } from "./HabitWidget";

registerModule({ id: "habit", title: "Habits", routes: [{ path: "/habits", element: HabitPage }],
  todayWidgets: [HabitWidget], commands: [{ id: "habits.open", label: "Habits'i ac", run: () => navigate("/habits") }],
});
