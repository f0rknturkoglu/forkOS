import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { RssPage } from "./RssPage";
import { RssWidget } from "./RssWidget";
import { RssStats } from "./RssStats";

registerModule({
  id: "rss",
  title: "RSS",
  routes: [{ path: "/rss", element: RssPage }],
  todayStats: [RssStats],
  todayWidgets: [RssWidget],
  commands: [
    { id: "rss.open", label: "RSS Reader'a git", run: () => navigate("/rss") },
    {
      id: "rss.read_all",
      label: "Tum RSS yazilarini okundu isaretle",
      run: async () => {
        if (confirm("Tum okunmamis yazilar okundu sayilsin mi?")) {
          await api.post("/rss/read-all");
          location.reload();
        }
      },
    },
  ],
});
