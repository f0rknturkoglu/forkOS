import { Wallet } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { FinancePage } from "./FinancePage";
import { RecurringWidget } from "./RecurringWidget";

registerModule({ id: "finance", title: "Finans", icon: Wallet, group: "track", searchLabel: "Finance", routes: [{ path: "/finance", element: FinancePage }], todayWidgets: [{ component: RecurringWidget, zone: "rhythm" }], commands: [{ id: "finance.open", label: "Finansı aç", run: () => navigate("/finance") }] });
