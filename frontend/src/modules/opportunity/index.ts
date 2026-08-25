import { lazy } from "react";
import { Target } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { DeadlineWidget, FollowupWidget, NotificationWidget } from "./OpportunityWidget";

const OpportunityPage = lazy(() => import("./OpportunityPage").then((module) => ({ default: module.OpportunityPage })));

registerModule({
  id: "opportunity",
  title: "Fırsatlar",
  icon: Target,
  group: "track",
  routes: [{ path: "/opportunities", element: OpportunityPage }],
  todayWidgets: [
    { component: DeadlineWidget, slot: "right", order: 20 },
    { component: FollowupWidget, slot: "right", order: 25 },
    { component: NotificationWidget, slot: "right", order: 30 },
  ],
  commands: [{ id: "opportunity.open", label: "Fırsatları aç", run: () => navigate("/opportunities") }],
});
