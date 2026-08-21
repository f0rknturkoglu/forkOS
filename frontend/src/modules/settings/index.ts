import { SlidersHorizontal } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { SettingsPage } from "./SettingsPage";

registerModule({ id: "settings", title: "Ayarlar", icon: SlidersHorizontal, group: "system", routes: [{ path: "/settings", element: SettingsPage }], commands: [{ id: "settings.open", label: "Ayarları aç", run: () => navigate("/settings") }] });
