import { lazy } from "react";
import { Home } from "lucide-react";
import { registerModule } from "@/core/registry";
import { TodayAgendaWidget } from "./TodayAgendaWidget";
import { DailyRhythmWidget } from "./DailyRhythmWidget";
import { FeedStreamWidget } from "./widgets/FeedStreamWidget";
import { PendingDecisions } from "./PendingDecisions";
import { QuickLinksWidget } from "./widgets/QuickLinksWidget";
import { NowNextWidget } from "./NowNextWidget";
import { DeadlinesWidget } from "./DeadlinesWidget";
import { CareerWidget } from "./CareerWidget";

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
  //
  // `core` anlamsal iskeleti kurar. `placement` ise isteğe bağlı widget'ın
  // konumudur; görünürlük/sıra tercihini değiştirmez.
  todayWidgets: [
    {
      // H7 karar yuzeyi dikkat alanında kalır; boşken yer tutmaz.
      // Bos liste hicbir sey cizmez (kendi icinde null doner).
      id: "today.pending-decisions",
      title: "Bekleyen kararlar",
      component: PendingDecisions,
      core: "attention",
      order: 10,
    },
    {
      // Günün yürütme işinin ana yüzeyi.
      id: "today.agenda",
      title: "Bugünün planı",
      component: TodayAgendaWidget,
      core: "plan",
      order: 20,
    },
    {
      // P2 §22: gercek son tarihler listesi; kariyer son tarihleri asagidaki
      // Kariyer kartinda baglamiyla gosterilir (ayni kayit iki kez cizilmez).
      id: "today.deadlines",
      title: "Son tarihler",
      component: DeadlinesWidget,
      core: "attention",
      order: 30,
    },
    {
      // P2 §24: takipler + kariyer bildirimleri + firsat son tarihleri.
      // Genel bildirimler ust seritteki panelde kalir.
      id: "today.career",
      title: "Kariyer",
      component: CareerWidget,
      core: "context",
      order: 40,
    },
    {
      // P2 §15: okuma akisi Home'un cekirdek yuzeyi (orta kolon).
      id: "today.feed-stream",
      title: "Akış",
      component: FeedStreamWidget,
      core: "context",
      order: 50,
    },
    {
      // P2 §21: "sira" sorusunu yanitlar; gunun planiyla ayni sorguyu paylasir.
      // Cekirdek degil: saatli isi olmayan gunlerde kendini cizmez.
      id: "today.now-next",
      title: "Şimdi ve sırada",
      component: NowNextWidget,
      placement: "now",
      order: 8,
    },
    {
      id: "today.rhythm",
      title: "Gün özeti",
      component: DailyRhythmWidget,
      order: 90,
      defaultVisible: false,
    },
    {
      id: "today.quick-links",
      title: "Hızlı bağlantılar",
      component: QuickLinksWidget,
      order: 95,
      defaultVisible: false,
    },
  ],
});
