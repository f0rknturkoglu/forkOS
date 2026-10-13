import { lazy } from "react";
import { Target } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
const GoalsPage = lazy(() => import("./GoalsPage").then((m) => ({ default: m.GoalsPage })));
registerModule({
  id: "goal",
  title: "Hedefler",
  description: "Hedeflerini adımlara ayır; görevlerini ve öğrenme çalışmalarını ilerlet.",
  icon: Target,
  routes: [{ path: "/goals", element: GoalsPage }],
  commands: [{ id: "goal.open", label: "Hedefleri aç", run: () => navigate("/goals") }],
});
