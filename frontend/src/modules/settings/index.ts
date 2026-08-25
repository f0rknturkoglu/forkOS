import { lazy } from "react";
import { SlidersHorizontal } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";

const SettingsPage = lazy(() => import("./SettingsPage").then((module) => ({ default: module.SettingsPage })));

registerModule({
  id: "settings",
  title: "Ayarlar",
  icon: SlidersHorizontal,
  group: "system",
  routes: [{ path: "/settings", element: SettingsPage }],
  commands: [{ id: "settings.open", label: "Ayarları aç", run: () => navigate("/settings") }],
});
