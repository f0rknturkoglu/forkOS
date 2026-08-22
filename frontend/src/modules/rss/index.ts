import { Rss } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { invalidate } from "@/core/queryClient";
import { confirmDialog } from "@/core/dialog";
import { RssPage } from "./RssPage";
import { RssStats } from "./RssStats";

registerModule({
  id: "rss",
  title: "RSS", icon: Rss, group: "capture",
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
        invalidate("items", "rss-stats", "feeds", "activity");
      },
    },
  ],
});
