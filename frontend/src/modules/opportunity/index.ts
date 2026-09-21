import { lazy } from "react";
import { Target } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { DeadlineWidget, FollowupWidget, NotificationWidget } from "./OpportunityWidget";

const OpportunityPage = lazy(() => import("./OpportunityPage").then((module) => ({ default: module.OpportunityPage })));

registerModule({
  id: "opportunity",
  // Gorunen ad Kariyer: is, basvuru, duyuru ve profil ayni calisma alani.
  title: "Kariyer",
  description: "İşleri keşfet, başvuruları ve duyuruları takip et, kariyer profilini yönet.",
  icon: Target,
  group: "track",
  routes: [{ path: "/opportunities", element: OpportunityPage }],
  todayWidgets: [
    { id: "opportunity.deadlines", title: "Son tarihler", component: DeadlineWidget, slot: "right", order: 20 },
    { id: "opportunity.followups", title: "Takip", component: FollowupWidget, slot: "right", order: 25 },
    { id: "opportunity.notifications", title: "Bildirimler", component: NotificationWidget, slot: "right", order: 30 },
  ],
  commands: [{ id: "opportunity.open", label: "Fırsatları aç", run: () => navigate("/opportunities") }],
});
