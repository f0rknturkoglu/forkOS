import { lazy } from "react";
import { HeartPulse } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { SourceHealthMiniWidget } from "./SourceHealthMiniWidget";
import { ServiceHealthWidget } from "./widgets/ServiceHealthWidget";

const HealthPage = lazy(() => import("./HealthPage").then((module) => ({ default: module.HealthPage })));
const SourceHealthPage = lazy(() =>
  import("./SourceHealthPage").then((module) => ({ default: module.SourceHealthPage })),
);

registerModule({
  id: "health",
  title: "Sağlık",
  icon: HeartPulse,
  group: "system",
  routes: [
    { path: "/health", element: HealthPage, title: "Sağlık" },
    { path: "/sources", element: SourceHealthPage, title: "Kaynaklar" },
  ],
  todayWidgets: [
    {
      id: "health.sources",
      title: "Kaynak sağlığı",
      component: SourceHealthMiniWidget,
      slot: "right",
      order: 95,
      defaultVisible: false,
    },
  ],
  commands: [
    { id: "health.open", label: "Sağlık panelini aç", run: () => navigate("/health") },
    { id: "sources.open", label: "Kaynakları aç", run: () => navigate("/sources") },
  ],
});
