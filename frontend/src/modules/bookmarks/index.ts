import { Bookmark } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { BookmarksPage } from "./BookmarksPage";
import { ReadingQueueWidget } from "./ReadingQueueWidget";

registerModule({
  id: "bookmarks",
  title: "Yer İmleri", icon: Bookmark, group: "capture",
  routes: [{ path: "/bookmarks", element: BookmarksPage }],
  todayWidgets: [{ component: ReadingQueueWidget, zone: "pending" }],
  commands: [
    { id: "bookmarks.open", label: "Yer İmleri’ni aç", run: () => navigate("/bookmarks") },
  ],
});
