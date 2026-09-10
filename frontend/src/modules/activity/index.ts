import { lazy } from "react";
import { Activity } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { ActivityWidget } from "./ActivityWidget";
import { Heatmap } from "./Heatmap";
import { RhythmWidget } from "./RhythmWidget";

const ActivityPage = lazy(() => import("./ActivityPage").then((module) => ({ default: module.ActivityPage })));
const DayPage = lazy(() => import("./DayPage").then((module) => ({ default: module.DayPage })));
const StatisticsRedirect = lazy(() =>
  import("./StatisticsRedirect").then((module) => ({ default: module.StatisticsRedirect })),
);

/**
 * Etkinlik & Ritim: emek haritasi, aylik trend ve hareket akisi TEK modulde.
 *
 * Onceden "Etkinlik" ve "Istatistikler" iki ayri moduldu; ikisi de ayni
 * `event` tablosunu farkli filtrelerle sayiyordu (harita insan islerini,
 * istatistik tum kayitlari) ve sidebar'da iki giris tutuyordu. Sayaclar artik
 * backend'de tek katalogdan gelir (statistics/service.VERB_COUNTERS).
 */
registerModule({
  id: "activity",
  title: "Etkinlik & Ritim",
  description: "Emek haritanı, serini ve aylık ritmini tek ekranda incele.",
  icon: Activity,
  group: "system",
  routes: [
    { path: "/activity", element: ActivityPage },
    // Eski istatistik rotasi: kalici yonlendirme (yer imleri kirilmasin).
    { path: "/statistics", element: StatisticsRedirect, title: "İstatistikler", navigation: "hidden" },
    // Emek haritasi karesinin hedefi: #/day?d=YYYY-MM-DD
    { path: "/day", element: DayPage, title: "Gün" },
  ],
  todayWidgets: [
    // Harita akisin altinda: gunun listesi once, ritim ozeti hemen ardindan.
    {
      id: "activity.heatmap",
      title: "Emek haritası",
      component: Heatmap,
      slot: "center",
      order: 30,
      defaultVisible: true,
    },
    {
      id: "activity.rhythm",
      title: "Ritim",
      component: RhythmWidget,
      slot: "center",
      order: 31,
      defaultVisible: true,
    },
    {
      id: "activity.widget",
      title: "Etkinlik",
      component: ActivityWidget,
      slot: "right",
      order: 90,
      defaultVisible: false,
    },
  ],
  commands: [
    { id: "activity.open", label: "Etkinliği aç", run: () => navigate("/activity") },
    { id: "activity.statistics", label: "Ritim özetini aç", run: () => navigate("/activity") },
  ],
});
