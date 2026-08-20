import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { OpportunityPage } from "./OpportunityPage";
import { DeadlineWidget, NotificationWidget } from "./OpportunityWidget";
import { SourceHealthPage } from "./SourceHealthPage";

registerModule({ id: "opportunity", title: "Opportunities",
  routes: [{ path: "/opportunities", element: OpportunityPage }, { path: "/sources", element: SourceHealthPage }],
  todayWidgets: [DeadlineWidget, NotificationWidget],
  commands: [
    { id: "opportunity.open", label: "Opportunity Hub'ı aç", run: () => navigate("/opportunities") },
    { id: "sources.open", label: "Kaynak sağlığını aç", run: () => navigate("/sources") },
  ],
});
