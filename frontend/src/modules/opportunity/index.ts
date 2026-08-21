import { Target } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { OpportunityPage } from "./OpportunityPage";
import { DeadlineWidget, NotificationWidget } from "./OpportunityWidget";
import { SourceHealthPage } from "./SourceHealthPage";

registerModule({ id: "opportunity", title: "Fırsatlar", icon: Target, group: "track",
  routes: [
    { path: "/opportunities", element: OpportunityPage },
    { path: "/sources", element: SourceHealthPage, title: "Kaynaklar" },
  ],
  todayWidgets: [{ component: DeadlineWidget, zone: "pending" }, { component: NotificationWidget, zone: "pending" }],
  commands: [
    { id: "opportunity.open", label: "Fırsatları aç", run: () => navigate("/opportunities") },
    { id: "sources.open", label: "Kaynakları aç", run: () => navigate("/sources") },
  ],
});
