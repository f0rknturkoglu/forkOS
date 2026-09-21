import { lazy } from "react";
import { SlidersHorizontal } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { openCapture } from "@/core/CaptureDialog";

const SettingsPage = lazy(() => import("./SettingsPage").then((module) => ({ default: module.SettingsPage })));

registerModule({
  id: "settings",
  title: "Ayarlar",
  description: "Tema, modüller, entegrasyonlar ve yedekleme tercihlerini yönet.",
  icon: SlidersHorizontal,
  routes: [{ path: "/settings", element: SettingsPage }],
  commands: [
    { id: "settings.open", label: "Ayarları aç", run: () => navigate("/settings") },
    { id: "capture.open", label: "Hızlı yakala", run: () => openCapture() },
  ],
});
