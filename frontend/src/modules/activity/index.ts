import { lazy } from "react";
import { Activity, Flame } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { ActivityWidget } from "./ActivityWidget";
import { HomeHeatmap } from "./Heatmap";
import { RhythmWidget } from "./RhythmWidget";

const ActivityPage = lazy(() => import("./ActivityPage").then((module) => ({ default: module.ActivityPage })));
const DayPage = lazy(() => import("./DayPage").then((module) => ({ default: module.DayPage })));
const HeatmapPage = lazy(() => import("./HeatmapPage").then((module) => ({ default: module.HeatmapPage })));
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
  routes: [
    { path: "/activity", element: ActivityPage },
    // Eski istatistik rotasi: kalici yonlendirme (yer imleri kirilmasin).
    { path: "/statistics", element: StatisticsRedirect, title: "İstatistikler", navigation: "hidden" },
    // Emek haritasi karesinin hedefi: #/day?d=YYYY-MM-DD
    { path: "/day", element: DayPage, title: "Gün" },
    // Harita artik Etkinlik sayfasinin ICINDE yasar (aralik secici de orada).
    // Kendi sayfasi yalniz eski baglantilar icin durur; sidebar satiri tutmaz.
    { path: "/activity/heatmap", element: HeatmapPage, title: "Isı Haritası", icon: Flame, navigation: "hidden" },
  ],
  todayWidgets: [
    {
      // Isı haritası Home'un çekirdek bağlam yüzeyidir.
      // Home kompakt surumu kullanir: ayni bilesen, ayni sorgu anahtari --
      // tam tur kirilimi ve aralik secimi Etkinlik sayfasinda kalir.
      id: "activity.heatmap",
      title: "Isı haritası",
      component: HomeHeatmap,
      core: "context",
      order: 70,
    },
    {
      id: "activity.rhythm",
      title: "Ritim",
      component: RhythmWidget,
      order: 31,
      defaultVisible: false,
    },
    {
      id: "activity.widget",
      title: "Etkinlik",
      component: ActivityWidget,
      order: 90,
      defaultVisible: false,
    },
  ],
  commands: [
    { id: "activity.open", label: "Etkinliği aç", run: () => navigate("/activity") },
    { id: "activity.statistics", label: "Ritim özetini aç", run: () => navigate("/activity") },
  ],
});
