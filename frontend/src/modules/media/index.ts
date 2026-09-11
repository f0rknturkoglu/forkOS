import { lazy } from "react";
import { Film } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { MediaContinueWidget } from "./MediaWidget";
import { MediaSidebar } from "./MediaSidebar";

const MediaPage = lazy(() => import("./MediaPage").then((module) => ({ default: module.MediaPage })));
const MediaDetailPage = lazy(() => import("./MediaDetailPage").then((module) => ({ default: module.MediaDetailPage })));
const MediaCollectionsPage = lazy(() =>
  import("./MediaCollectionsPage").then((module) => ({ default: module.MediaCollectionsPage })),
);
const MediaCollectionDetailPage = lazy(() =>
  import("./MediaCollectionDetailPage").then((module) => ({ default: module.MediaCollectionDetailPage })),
);
const MediaUpcomingPage = lazy(() =>
  import("./MediaUpcomingPage").then((module) => ({ default: module.MediaUpcomingPage })),
);
const MediaStatsPage = lazy(() => import("./MediaStatsPage").then((module) => ({ default: module.MediaStatsPage })));
const MediaTrashPage = lazy(() => import("./MediaTrashPage").then((module) => ({ default: module.MediaTrashPage })));

registerModule({
  id: "media",
  title: "Medya",
  description: "Film, dizi, anime, manga, kitap, sesli kitap, podcast, müzik ve oyunlarını tek kütüphanede takip et.",
  icon: Film,
  group: "track",
  sidebar: MediaSidebar,
  routes: [
    { path: "/media", element: MediaPage },
    { path: "/media/library", element: MediaPage },
    { path: "/media/collections", element: MediaCollectionsPage },
    // Statik `/media/:id` detay rotası bu satırı ezmesin diye önce gelir.
    { path: "/media/collections/:id", element: MediaCollectionDetailPage },
    { path: "/media/upcoming", element: MediaUpcomingPage },
    { path: "/media/stats", element: MediaStatsPage },
    { path: "/media/trash", element: MediaTrashPage },
    { path: "/media/:id", element: MediaDetailPage },
  ],
  todayWidgets: [
    {
      id: "media.continue",
      title: "Devam eden medya",
      component: MediaContinueWidget,
      slot: "right",
      order: 70,
      defaultVisible: false,
    },
  ],
  commands: [
    { id: "media.open", label: "Medya kütüphanesini aç", run: () => navigate("/media") },
    {
      id: "media.search_catalog",
      label: "Medya kataloğunda ara",
      run: () => navigate("/media?search=1"),
    },
  ],
});
