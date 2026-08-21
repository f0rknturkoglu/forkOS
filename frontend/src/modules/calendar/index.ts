import { Calendar } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { CalendarPage } from "./CalendarPage";
import { TodayScheduleWidget } from "./TodayScheduleWidget";

registerModule({ id: "calendar", title: "Takvim", icon: Calendar, group: "do", routes: [{ path: "/calendar", element: CalendarPage }], todayWidgets: [{ component: TodayScheduleWidget, zone: "now" }], commands: [{ id: "calendar.open", label: "Takvimi aç", run: () => navigate("/calendar") }] });
