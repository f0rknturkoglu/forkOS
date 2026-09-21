import { lazy } from "react";
import { Target } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";

const OpportunityPage = lazy(() => import("./OpportunityPage").then((module) => ({ default: module.OpportunityPage })));

registerModule({
  id: "opportunity",
  // Gorunen ad Kariyer: is, basvuru, duyuru ve profil ayni calisma alani.
  title: "Kariyer",
  description: "İşleri keşfet, başvuruları ve duyuruları takip et, kariyer profilini yönet.",
  icon: Target,
  routes: [{ path: "/opportunities", element: OpportunityPage }],
  // Son tarih/takip/bildirim Home'da artik TEK "Dikkat" yuzeyinde toplanir
  // (`today.attention`); bu modul kendi basina ayri widget tutmaz.
  commands: [{ id: "opportunity.open", label: "Fırsatları aç", run: () => navigate("/opportunities") }],
});
