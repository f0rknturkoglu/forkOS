import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { CalendarPage } from "./CalendarPage";
import { TodayScheduleWidget } from "./TodayScheduleWidget";

registerModule({ id: "calendar", title: "Calendar", routes: [{ path: "/calendar", element: CalendarPage }], todayWidgets: [TodayScheduleWidget], commands: [{ id: "calendar.open", label: "Takvimi aç", run: () => navigate("/calendar") }] });
