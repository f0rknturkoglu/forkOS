import { Sun } from "lucide-react";
import { registerModule } from "@/core/registry";
import { TodayPage } from "./TodayPage";

registerModule({
  id: "today",
  title: "Bugün", icon: Sun, group: "pinned",
  routes: [{ path: "/", element: TodayPage }],
});
