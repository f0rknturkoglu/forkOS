import { lazy } from "react";
import { Calendar } from "lucide-react";
import { CalendarWidget } from "./CalendarWidget";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";

const CalendarPage = lazy(() => import("./CalendarPage").then((module) => ({ default: module.CalendarPage })));

registerModule({
  id: "calendar",
  title: "Takvim",
  description: "Etkinliklerini takvimde planla, gün ve hafta görünümünde izle.",
  icon: Calendar,
  routes: [{ path: "/calendar", element: CalendarPage }],
  todayWidgets: [
    {
      id: "calendar.events",
      title: "Takvim",
      component: CalendarWidget,
      slot: "right",
      order: 35,
      defaultVisible: false,
    },
  ],
  commands: [{ id: "calendar.open", label: "Takvimi aç", run: () => navigate("/calendar") }],
});
