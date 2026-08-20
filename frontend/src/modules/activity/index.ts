import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { ActivityPage } from "./ActivityPage";
import { ActivityWidget } from "./ActivityWidget";

registerModule({
  id: "activity",
  title: "Activity",
  routes: [{ path: "/activity", element: ActivityPage }],
  todayWidgets: [ActivityWidget],
  commands: [
    { id: "activity.open", label: "Activity'ye git", run: () => navigate("/activity") },
  ],
});
