import { invalidateAfter } from "@/core/invalidation";
import { lazy } from "react";
import { Newspaper, Rss } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { RssStats } from "./RssStats";

const RssPage = lazy(() => import("./RssPage").then((module) => ({ default: module.RssPage })));
const FeedPage = lazy(() => import("./FeedPage").then((module) => ({ default: module.FeedPage })));

registerModule({
  id: "rss",
  title: "RSS",
  description: "RSS aboneliklerini takip et, yeni yazıları oku ve okundu işaretle.",
  icon: Rss,
  routes: [
    { path: "/rss", element: RssPage },
    // Okuma akisi: RSS + Reddit + Hacker News + GitHub tek listede. Home'un ve
    // RSS sayfasinin parcasidir; Kutuphane'de AYRI satir tutmaz (rota durur).
    { path: "/feed", element: FeedPage, title: "Okuma Akışı", icon: Newspaper, navigation: "hidden" },
  ],
  todayStats: [RssStats],
  commands: [
    { id: "feed.open", label: "Okuma akışını aç", run: () => navigate("/feed") },
    { id: "rss.open", label: "RSS’i aç", run: () => navigate("/rss") },
    {
      id: "rss.read_all",
      label: "Tüm RSS yazılarını okundu işaretle",
      run: async () => {
        const ok = await confirmDialog({
          title: "Tümü okundu sayılsın mı?",
          body: "Okunmamış bütün yazılar okundu işaretlenecek. Tek tek geri almak gerekir.",
          confirmLabel: "Okundu işaretle",
        });
        if (!ok) return;
        await api.post("/rss/read-all");
        invalidateAfter("rss.write");
      },
    },
  ],
});
