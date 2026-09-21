import { lazy } from "react";
import { Home } from "lucide-react";
import { registerModule } from "@/core/registry";
import { TodayAgendaWidget } from "./TodayAgendaWidget";
import { DailyRhythmWidget } from "./DailyRhythmWidget";
import { FeedStreamWidget } from "./widgets/FeedStreamWidget";
import { PendingDecisions } from "./PendingDecisions";
import { QuickLinksWidget } from "./widgets/QuickLinksWidget";
import { AttentionWidget } from "./AttentionWidget";
import { NowNextWidget } from "./NowNextWidget";

const TodayPage = lazy(() => import("./TodayPage").then((module) => ({ default: module.TodayPage })));

registerModule({
  id: "today",
  // Gorunen ad Home; teknik ad alani (`today`, `today.*` ayarlari, widget
  // kimlikleri) sozlesme olarak DEGISMEZ (bkz. docs/product-navigation.md).
  title: "Home",
  description: "Günün planını, dikkat isteyen işleri ve bekleyen kararları tek ekranda gör.",
  icon: Home,
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
      // Karar yuzeyi ana icerikten ONCE, tam genislikte (bosken hic cizilmez).
      region: "priority",
      order: 1,
    },
    {
      id: "today.rhythm",
      title: "Gün özeti",
      component: DailyRhythmWidget,
      region: "secondary",
      order: 5,
      defaultVisible: false,
    },
    {
      // P2: Home once "sira" sorusunu yanitlar, sonra gunun plani gelir.
      id: "today.now-next",
      title: "Şimdi ve sırada",
      component: NowNextWidget,
      region: "main",
      order: 8,
    },
    { id: "today.agenda", title: "Bugünün planı", component: TodayAgendaWidget, region: "main", order: 10 },
    {
      // Akis ikincil: varsayilan Home'da dikkat calmaz, Ayarlar > Home'dan acilir.
      id: "today.feed-stream",
      title: "Akış",
      component: FeedStreamWidget,
      region: "secondary",
      order: 10,
      defaultVisible: false,
    },
    {
      // P2 §23: tek dikkat yuzeyi; son tarihler + takipler + okunmamis bildirimler.
      id: "today.attention",
      title: "Dikkat",
      component: AttentionWidget,
      region: "rail",
      order: 2,
    },
    {
      id: "today.quick-links",
      title: "Hızlı bağlantılar",
      component: QuickLinksWidget,
      region: "secondary",
      order: 80,
      defaultVisible: false,
    },
  ],
});
