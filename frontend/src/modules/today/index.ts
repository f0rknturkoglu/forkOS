import { lazy } from "react";
import { Sun } from "lucide-react";
import { registerModule } from "@/core/registry";
import { TodayAgendaWidget } from "./TodayAgendaWidget";
import { DailyRhythmWidget } from "./DailyRhythmWidget";
import { FeedStreamWidget } from "./widgets/FeedStreamWidget";
import { QuickLinksWidget } from "./widgets/QuickLinksWidget";

const TodayPage = lazy(() => import("./TodayPage").then((module) => ({ default: module.TodayPage })));

registerModule({
  id: "today",
  title: "Bugün",
  description: "Günün planını, akışını ve hızlı bağlantılarını tek ekranda gör.",
  icon: Sun,
  group: "pinned",
  routes: [{ path: "/", element: TodayPage }],
  // Saat + hava ust seritte (TodayHero); sunucu ve saglik ust seritteki
  // durum LED'inde (StatusLed) -- panelde tekrar etmezler.
  // orta = akis, sag = durum. Sira icin bkz. TodayWidget.order.
  todayWidgets: [
    {
      id: "today.rhythm",
      title: "Gün özeti",
      component: DailyRhythmWidget,
      slot: "left",
      order: 5,
      defaultVisible: false,
    },
    { id: "today.agenda", title: "Bugünün planı", component: TodayAgendaWidget, slot: "left", order: 10 },
    {
      id: "today.feed-stream",
      title: "Akış",
      component: FeedStreamWidget,
      slot: "center",
      order: 10,
      defaultVisible: true,
    },
    {
      id: "today.quick-links",
      title: "Hızlı bağlantılar",
      component: QuickLinksWidget,
      slot: "right",
      order: 80,
      defaultVisible: false,
    },
  ],
});
