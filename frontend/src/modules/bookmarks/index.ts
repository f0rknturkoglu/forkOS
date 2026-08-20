import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { BookmarksPage } from "./BookmarksPage";
import { ReadingQueueWidget } from "./ReadingQueueWidget";

registerModule({
  id: "bookmarks",
  title: "Bookmarks",
  routes: [{ path: "/bookmarks", element: BookmarksPage }],
  todayWidgets: [ReadingQueueWidget],
  commands: [
    { id: "bookmarks.open", label: "Bookmark Library'e git", run: () => navigate("/bookmarks") },
  ],
});
