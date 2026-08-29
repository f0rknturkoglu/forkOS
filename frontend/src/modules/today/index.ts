import { lazy } from "react";
import { Sun } from "lucide-react";
import { registerModule } from "@/core/registry";
import { TodayAgendaWidget } from "./TodayAgendaWidget";
import { FeedStreamWidget } from "./widgets/FeedStreamWidget";
import { QuickLinksWidget } from "./widgets/QuickLinksWidget";

const TodayPage = lazy(() => import("./TodayPage").then((module) => ({ default: module.TodayPage })));

registerModule({
  id: "today",
  title: "Bugün",
  icon: Sun,
  group: "pinned",
  routes: [{ path: "/", element: TodayPage }],
  // Saat + hava ust seritte (TodayHero); sunucu ve saglik ust seritteki
  // durum LED'inde (StatusLed) -- panelde tekrar etmezler.
  // orta = akis, sag = durum. Sira icin bkz. TodayWidget.order.
  todayWidgets: [
    { id: "today.agenda", title: "Günün akışı", component: TodayAgendaWidget, slot: "left", order: 10 },
    { id: "today.feed-stream", title: "Akış", component: FeedStreamWidget, slot: "center", order: 10 },
    { id: "today.quick-links", title: "Hızlı bağlantılar", component: QuickLinksWidget, slot: "right", order: 80 },
  ],
});
