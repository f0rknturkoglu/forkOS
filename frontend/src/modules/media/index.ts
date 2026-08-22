import { Film } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { MediaPage } from "./MediaPage";

registerModule({
  id: "media",
  title: "Medya",
  icon: Film,
  group: "track",
  routes: [{ path: "/media", element: MediaPage }],
  commands: [{ id: "media.open", label: "Medya kütüphanesini aç", run: () => navigate("/media") }],
});
