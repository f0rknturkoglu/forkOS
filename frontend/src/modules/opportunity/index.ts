import { lazy } from "react";
import { Target } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { DeadlineWidget, FollowupWidget, NotificationWidget } from "./OpportunityWidget";

const OpportunityPage = lazy(() => import("./OpportunityPage").then((module) => ({ default: module.OpportunityPage })));
const SourceHealthPage = lazy(() => import("./SourceHealthPage").then((module) => ({ default: module.SourceHealthPage })));

registerModule({ id: "opportunity", title: "Fırsatlar", icon: Target, group: "track",
  routes: [
    { path: "/opportunities", element: OpportunityPage },
    { path: "/sources", element: SourceHealthPage, title: "Kaynaklar" },
  ],
  todayWidgets: [{ component: DeadlineWidget, zone: "pending", slot: "right", order: 20 }, { component: FollowupWidget, zone: "pending", slot: "right", order: 25 }, { component: NotificationWidget, zone: "pending", slot: "right", order: 30 }],
  commands: [
    { id: "opportunity.open", label: "Fırsatları aç", run: () => navigate("/opportunities") },
    { id: "sources.open", label: "Kaynakları aç", run: () => navigate("/sources") },
  ],
});