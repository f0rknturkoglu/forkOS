import { registerModule } from "@/core/registry";
import { TodayPage } from "./TodayPage";

registerModule({
  id: "today",
  title: "Today",
  routes: [{ path: "/", element: TodayPage }],
});
