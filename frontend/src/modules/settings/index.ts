import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { SettingsPage } from "./SettingsPage";

registerModule({ id: "settings", title: "Settings", routes: [{ path: "/settings", element: SettingsPage }], commands: [{ id: "settings.open", label: "Ayarları aç", run: () => navigate("/settings") }] });
