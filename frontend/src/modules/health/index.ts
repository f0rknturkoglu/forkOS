import { lazy } from "react";
import { HeartPulse } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { SourceHealthMiniWidget } from "./SourceHealthMiniWidget";

const HealthPage = lazy(() => import("./HealthPage").then((module) => ({ default: module.HealthPage })));

registerModule({
  id: "health",
  title: "Sağlık",
  icon: HeartPulse,
  group: "system",
  routes: [{ path: "/health", element: HealthPage, title: "Sağlık" }],
  todayWidgets: [{ component: SourceHealthMiniWidget, slot: "right", order: 95 }],
  commands: [
    { id: "health.open", label: "Sağlık panelini aç", run: () => navigate("/health") },
  ],
});
