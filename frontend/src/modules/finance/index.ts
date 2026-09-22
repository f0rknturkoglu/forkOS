import { lazy } from "react";
import { Wallet } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { RecurringWidget } from "./RecurringWidget";
/**
 * CSV export ucundaki tablo adi (backend module_table_names sozlesmesi).
 * Modulun kendi veri kimligi; baska dosyada sabit yazilmaz.
 */
export const EXPORT_MODULE = "expense" as const;

const FinancePage = lazy(() => import("./FinancePage").then((module) => ({ default: module.FinancePage })));

registerModule({
  id: "finance",
  title: "Abonelikler",
  description: "Yaklaşan abonelik ödemelerini ve aylık toplamı takip et.",
  icon: Wallet,
  routes: [{ path: "/finance", element: FinancePage }],
  todayWidgets: [
    {
      id: "finance.recurring",
      title: "Düzenli ödemeler",
      component: RecurringWidget,
      order: 60,
      defaultVisible: false,
    },
  ],
  commands: [
    { id: "finance.open", label: "Abonelikleri aç", run: () => navigate("/finance") },
    { id: "finance.subs", label: "Abonelikleri aç", run: () => navigate("/finance") },
  ],
});
