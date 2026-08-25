import { lazy } from "react";
import { Film } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { MediaContinueWidget } from "./MediaWidget";

const MediaPage = lazy(() => import("./MediaPage").then((module) => ({ default: module.MediaPage })));
const MediaDetailPage = lazy(() => import("./MediaDetailPage").then((module) => ({ default: module.MediaDetailPage })));
const MediaCollectionsPage = lazy(() =>
  import("./MediaCollectionsPage").then((module) => ({ default: module.MediaCollectionsPage })),
);
const MediaUpcomingPage = lazy(() =>
  import("./MediaUpcomingPage").then((module) => ({ default: module.MediaUpcomingPage })),
);
const MediaStatsPage = lazy(() => import("./MediaStatsPage").then((module) => ({ default: module.MediaStatsPage })));
const MediaTrashPage = lazy(() => import("./MediaTrashPage").then((module) => ({ default: module.MediaTrashPage })));

registerModule({
  id: "media",
  title: "Medya",
  icon: Film,
  group: "track",
  routes: [
    { path: "/media", element: MediaPage },
    { path: "/media/library", element: MediaPage },
    { path: "/media/collections", element: MediaCollectionsPage },
    { path: "/media/upcoming", element: MediaUpcomingPage },
    { path: "/media/stats", element: MediaStatsPage },
    { path: "/media/trash", element: MediaTrashPage },
    { path: "/media/:id", element: MediaDetailPage },
  ],
  todayWidgets: [{ component: MediaContinueWidget, slot: "right", order: 70 }],
  commands: [{ id: "media.open", label: "Medya kütüphanesini aç", run: () => navigate("/media") }],
});
