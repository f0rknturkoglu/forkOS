import { Activity } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { ActivityPage } from "./ActivityPage";
import { ActivityWidget } from "./ActivityWidget";

registerModule({
  id: "activity",
  title: "Etkinlik", icon: Activity, group: "system",
  routes: [{ path: "/activity", element: ActivityPage }],
  todayWidgets: [{ component: ActivityWidget, zone: "rhythm" }],
  commands: [
    { id: "activity.open", label: "Etkinliği aç", run: () => navigate("/activity") },
  ],
});
