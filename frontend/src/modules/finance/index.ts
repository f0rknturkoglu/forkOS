import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { FinancePage } from "./FinancePage";
import { RecurringWidget } from "./RecurringWidget";

registerModule({ id: "finance", title: "Finance", searchLabel: "Finance", routes: [{ path: "/finance", element: FinancePage }], todayWidgets: [RecurringWidget], commands: [{ id: "finance.open", label: "Finansı aç", run: () => navigate("/finance") }] });
