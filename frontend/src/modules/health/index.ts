import { lazy } from "react";
import { HeartPulse, Radio } from "lucide-react";
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
  description: "Sunucu, servis ve veri kaynaklarının sağlık durumunu izle.",
  icon: HeartPulse,
  routes: [
    { path: "/health", element: HealthPage, title: "Sağlık" },
    { path: "/sources", element: SourceHealthPage, title: "Kaynaklar", icon: Radio, navigation: "child" },
  ],
  todayWidgets: [
    {
      id: "health.sources",
      title: "Kaynak sağlığı",
      component: SourceHealthMiniWidget,
      region: "secondary",
      order: 95,
      defaultVisible: false,
    },
  ],
  commands: [
    { id: "health.open", label: "Sağlık panelini aç", run: () => navigate("/health") },
    { id: "sources.open", label: "Kaynakları aç", run: () => navigate("/sources") },
  ],
});
