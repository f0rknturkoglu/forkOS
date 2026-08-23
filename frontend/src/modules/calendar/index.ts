import { Calendar } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { CalendarPage } from "./CalendarPage";

registerModule({ id: "calendar", title: "Takvim", icon: Calendar, group: "do", routes: [{ path: "/calendar", element: CalendarPage }], commands: [{ id: "calendar.open", label: "Takvimi aç", run: () => navigate("/calendar") }] });
