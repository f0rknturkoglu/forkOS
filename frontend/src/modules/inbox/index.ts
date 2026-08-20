import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { InboxPage } from "./InboxPage";
import { InboxWidget } from "./InboxWidget";
import { InboxStats } from "./InboxStats";

registerModule({
  id: "inbox",
  title: "Inbox",
  routes: [{ path: "/inbox", element: InboxPage }],
  todayStats: [InboxStats],
  todayWidgets: [InboxWidget],
  commands: [
    { id: "inbox.open", label: "Inbox'a git", run: () => navigate("/inbox") },
    {
      id: "inbox.capture",
      label: "Bookmark kaydet (URL yapistir)",
      run: async () => {
        const url = prompt("URL");
        if (!url) return;
        await api.post("/capture", {
          url: url.trim(),
          collection: "inbox",
          source: "manual",
          client_uuid: crypto.randomUUID(),
        });
        navigate("/inbox");
      },
    },
  ],
});
