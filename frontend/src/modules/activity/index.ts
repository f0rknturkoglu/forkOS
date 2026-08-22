import { Activity } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { ActivityPage } from "./ActivityPage";
import { DayPage } from "./DayPage";
import { ActivityWidget } from "./ActivityWidget";
import { Heatmap } from "./Heatmap";

registerModule({
  id: "activity",
  title: "Etkinlik", icon: Activity, group: "system",
  routes: [
    { path: "/activity", element: ActivityPage },
    // Emek haritasi karesinin hedefi: #/day?d=YYYY-MM-DD
    { path: "/day", element: DayPage, title: "Gün" },
  ],
  todayWidgets: [
    // Harita akisin altinda: gunun listesi once, yilin ozeti sonra.
    { component: Heatmap, zone: "rhythm", slot: "center", order: 30 },
    { component: ActivityWidget, zone: "rhythm", slot: "right", order: 90 },
  ],
  commands: [
    { id: "activity.open", label: "Etkinliği aç", run: () => navigate("/activity") },
  ],
});
