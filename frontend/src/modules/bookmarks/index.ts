import { lazy } from "react";
import { Bookmark } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { ReadingQueueWidget } from "./ReadingQueueWidget";

const BookmarksPage = lazy(() => import("./BookmarksPage").then((module) => ({ default: module.BookmarksPage })));

registerModule({
  id: "bookmarks",
  title: "Yer İmleri", icon: Bookmark, group: "capture",
  routes: [{ path: "/bookmarks", element: BookmarksPage }],
  todayWidgets: [{ component: ReadingQueueWidget, slot: "right", order: 50 }],
  commands: [
    { id: "bookmarks.open", label: "Yer İmleri’ni aç", run: () => navigate("/bookmarks") },
  ],
});
