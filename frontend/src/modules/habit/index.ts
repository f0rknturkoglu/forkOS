import { Repeat } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { HabitPage } from "./HabitPage";
import { HabitWidget } from "./HabitWidget";

registerModule({ id: "habit", title: "Alışkanlıklar", icon: Repeat, group: "track", routes: [{ path: "/habits", element: HabitPage }],
  todayWidgets: [{ component: HabitWidget, zone: "rhythm" }], commands: [{ id: "habits.open", label: "Alışkanlıkları aç", run: () => navigate("/habits") }],
});
