import { invalidateAfter } from "@/core/invalidation";
import { lazy } from "react";
import { Rss } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { invalidate } from "@/core/queryClient";
import { confirmDialog } from "@/core/dialog";
import { RssStats } from "./RssStats";

const RssPage = lazy(() => import("./RssPage").then((module) => ({ default: module.RssPage })));

registerModule({
  id: "rss",
  title: "RSS",
  icon: Rss,
  group: "capture",
  routes: [{ path: "/rss", element: RssPage }],
  todayStats: [RssStats],
  commands: [
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
