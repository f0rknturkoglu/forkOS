import { lazy } from "react";
import { Film } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { MediaContinueWidget } from "./MediaWidget";

const MediaPage = lazy(() => import("./MediaPage").then((module) => ({ default: module.MediaPage })));

registerModule({
  id: "media",
  title: "Medya",
  icon: Film,
  group: "track",
  routes: [{ path: "/media", element: MediaPage }],
  todayWidgets: [{ component: MediaContinueWidget, zone: "rhythm", slot: "right", order: 70 }],
  commands: [{ id: "media.open", label: "Medya kütüphanesini aç", run: () => navigate("/media") }],
});
