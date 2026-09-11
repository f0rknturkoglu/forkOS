import { invalidateAfter } from "@/core/invalidation";
import { lazy } from "react";
import { Inbox } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { InboxTodayWidget } from "./InboxTodayWidget";
import { InboxStats } from "./InboxStats";

const InboxPage = lazy(() => import("./InboxPage").then((module) => ({ default: module.InboxPage })));

registerModule({
  id: "inbox",
  title: "Gelen Kutusu",
  description: "Gelen bağlantı ve notları tek kuyrukta topla, sonra düzenle.",
  icon: Inbox,
  hidden: true,
  routes: [{ path: "/inbox", element: InboxPage }],
  todayStats: [InboxStats],
  todayWidgets: [{ id: "inbox.widget", title: "Gelen kutusu", component: InboxTodayWidget, slot: "right", order: 40 }],
  commands: [
    { id: "inbox.open", label: "Gelen kutusunu aç", run: () => navigate("/today?triage=inbox") },
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
        invalidateAfter("bookmark.write");
        navigate("/today?triage=inbox");
      },
    },
  ],
});
