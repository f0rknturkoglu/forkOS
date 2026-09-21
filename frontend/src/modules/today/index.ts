import { lazy } from "react";
import { Home } from "lucide-react";
import { registerModule } from "@/core/registry";
import { TodayAgendaWidget } from "./TodayAgendaWidget";
import { DailyRhythmWidget } from "./DailyRhythmWidget";
import { FeedStreamWidget } from "./widgets/FeedStreamWidget";
import { PendingDecisions } from "./PendingDecisions";
import { QuickLinksWidget } from "./widgets/QuickLinksWidget";

const TodayPage = lazy(() => import("./TodayPage").then((module) => ({ default: module.TodayPage })));

registerModule({
  id: "today",
  // Gorunen ad Home; teknik ad alani (`today`, `today.*` ayarlari, widget
  // kimlikleri) sozlesme olarak DEGISMEZ (bkz. docs/product-navigation.md).
  title: "Home",
  description: "Günün planını, dikkat isteyen işleri ve bekleyen kararları tek ekranda gör.",
  icon: Home,
  group: "pinned",
  routes: [{ path: "/", element: TodayPage }],
  // Saat + hava ust seritte (TodayHero); sunucu ve saglik ust seritteki
  // durum LED'inde (StatusLed) -- panelde tekrar etmezler.
  // orta = akis, sag = durum. Sira icin bkz. TodayWidget.order.
  todayWidgets: [
    {
      // H7 karar yuzeyi: bekleyen planlar gunun isine girmeden once gorulur.
      // Bos liste hicbir sey cizmez (kendi icinde null doner).
      id: "today.pending-decisions",
      title: "Bekleyen kararlar",
      component: PendingDecisions,
      slot: "left",
      order: 1,
    },
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
