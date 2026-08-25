import { lazy } from "react";
import { GraduationCap } from "lucide-react";
import { LearningWidget } from "./LearningWidget";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";

const LearningPage = lazy(() => import("./LearningPage").then((module) => ({ default: module.LearningPage })));

registerModule({ id: "learning", title: "Öğrenme", icon: GraduationCap, group: "track", routes: [{ path: "/learning", element: LearningPage }], todayWidgets: [{ component: LearningWidget, slot: "left", order: 65 }], commands: [{ id: "learning.open", label: "Kurs, kitap ve öğrenme kuyruğunu aç", run: () => navigate("/learning") }] });
