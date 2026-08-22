import { Sun } from "lucide-react";
import { registerModule } from "@/core/registry";
import { TodayPage } from "./TodayPage";
import { FeedStreamWidget } from "./widgets/FeedStreamWidget";
import { QuickLinksWidget } from "./widgets/QuickLinksWidget";

registerModule({
  id: "today",
  title: "Bugün", icon: Sun, group: "pinned",
  routes: [{ path: "/", element: TodayPage }],
  // Saat + hava ust seritte (TodayHero); sunucu ve saglik ust seritteki
  // durum LED'inde (StatusLed) -- panelde tekrar etmezler.
  // orta = akis, sag = durum. Sira icin bkz. TodayWidget.order.
  todayWidgets: [
    { component: FeedStreamWidget, zone: "rhythm", slot: "center", order: 10 },
    { component: QuickLinksWidget, zone: "rhythm", slot: "right", order: 80 },
  ],
});
