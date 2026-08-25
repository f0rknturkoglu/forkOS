import { lazy } from "react";
import { Wallet } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { RecurringWidget } from "./RecurringWidget";

const FinancePage = lazy(() => import("./FinancePage").then((module) => ({ default: module.FinancePage })));

registerModule({
  id: "finance",
  title: "Finans",
  icon: Wallet,
  group: "track",
  routes: [{ path: "/finance", element: FinancePage }],
  todayWidgets: [{ component: RecurringWidget, slot: "right", order: 60 }],
  commands: [{ id: "finance.open", label: "Finansı aç", run: () => navigate("/finance") }],
});
