import { lazy } from "react";
import { Calendar } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";

const CalendarPage = lazy(() => import("./CalendarPage").then((module) => ({ default: module.CalendarPage })));

registerModule({ id: "calendar", title: "Takvim", icon: Calendar, group: "do", routes: [{ path: "/calendar", element: CalendarPage }], commands: [{ id: "calendar.open", label: "Takvimi aç", run: () => navigate("/calendar") }] });
