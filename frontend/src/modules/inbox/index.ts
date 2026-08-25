import { lazy } from "react";
import { Inbox } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { invalidate } from "@/core/queryClient";
import { InboxWidget } from "./InboxWidget";
import { InboxStats } from "./InboxStats";

const InboxPage = lazy(() => import("./InboxPage").then((module) => ({ default: module.InboxPage })));

registerModule({
  id: "inbox",
  title: "Gelen Kutusu", icon: Inbox, group: "capture",
  routes: [{ path: "/inbox", element: InboxPage }],
  todayStats: [InboxStats],
  todayWidgets: [{ component: InboxWidget, slot: "right", order: 40 }],
  commands: [
    { id: "inbox.open", label: "Gelen kutusunu aç", run: () => navigate("/inbox") },
    {
      id: "inbox.capture",
      label: "Bağlantı kaydet",
      ask: { label: "Kaydedilecek URL", placeholder: "https://…" },
      run: async (url) => {
        if (!url) return;
        await api.post("/capture", {
          url: url.trim(),
          collection: "inbox",
          source: "manual",
          client_uuid: crypto.randomUUID(),
        });
        invalidate("bookmarks", "bookmark-stats", "activity");
        navigate("/inbox");
      },
    },
  ],
});
