import { lazy } from "react";
import { HeartPulse } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";

const HealthPage = lazy(() => import("./HealthPage").then((module) => ({ default: module.HealthPage })));

registerModule({
  id: "health",
  title: "Sağlık",
  icon: HeartPulse,
  group: "system",
  routes: [{ path: "/health", element: HealthPage, title: "Sağlık" }],
  commands: [
    { id: "health.open", label: "Sağlık panelini aç", run: () => navigate("/health") },
  ],
});
