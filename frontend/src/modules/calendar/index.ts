import { lazy } from "react";
import { Calendar } from "lucide-react";
import { CalendarWidget } from "./CalendarWidget";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";

const CalendarPage = lazy(() => import("./CalendarPage").then((module) => ({ default: module.CalendarPage })));

registerModule({ id: "calendar", title: "Takvim", icon: Calendar, group: "do", routes: [{ path: "/calendar", element: CalendarPage }], todayWidgets: [{ component: CalendarWidget, slot: "right", order: 35 }], commands: [{ id: "calendar.open", label: "Takvimi aç", run: () => navigate("/calendar") }] });
