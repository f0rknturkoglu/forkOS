import { lazy } from "react";
import { BarChart3 } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { StatisticsWidget } from "./StatisticsWidget";

const StatisticsPage = lazy(() =>
  import("./StatisticsPage").then((module) => ({ default: module.StatisticsPage })),
);

registerModule({
  id: "statistics",
  title: "İstatistikler",
  icon: BarChart3,
  group: "system",
  routes: [{ path: "/statistics", element: StatisticsPage, title: "İstatistikler" }],
  todayWidgets: [
    // Emek haritasi (order 30) HEMEN altina; kullanici heatmap + istatistik
    // ayni arada gorur.
    {
      id: "statistics.summary",
      title: "İstatistikler",
      component: StatisticsWidget,
      slot: "center",
      order: 31,
      defaultVisible: true,
    },
  ],
  commands: [
    { id: "statistics.open", label: "İstatistikleri aç", run: () => navigate("/statistics") },
  ],
});
