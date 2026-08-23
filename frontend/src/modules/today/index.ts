import { lazy } from "react";
import { Sun } from "lucide-react";
import { registerModule } from "@/core/registry";
import { TodayAgendaWidget } from "./TodayAgendaWidget";
import { FeedStreamWidget } from "./widgets/FeedStreamWidget";
import { QuickLinksWidget } from "./widgets/QuickLinksWidget";

const TodayPage = lazy(() => import("./TodayPage").then((module) => ({ default: module.TodayPage })));

registerModule({
  id: "today",
  title: "Bugün", icon: Sun, group: "pinned",
  routes: [{ path: "/", element: TodayPage }],
  // Saat + hava ust seritte (TodayHero); sunucu ve saglik ust seritteki
  // durum LED'inde (StatusLed) -- panelde tekrar etmezler.
  // orta = akis, sag = durum. Sira icin bkz. TodayWidget.order.
  todayWidgets: [
    { component: TodayAgendaWidget, zone: "now", slot: "left", order: 10 },
    { component: FeedStreamWidget, zone: "rhythm", slot: "center", order: 10 },
    { component: QuickLinksWidget, zone: "rhythm", slot: "right", order: 80 },
  ],
});
