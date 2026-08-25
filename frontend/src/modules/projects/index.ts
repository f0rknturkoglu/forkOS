import { lazy } from "react";
import { Layers } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { ProjectsWidget } from "./ProjectsWidget";

const ProjectsPage = lazy(() => import("./ProjectsPage").then((module) => ({ default: module.ProjectsPage })));

registerModule({ id: "projects", title: "Projeler", icon: Layers, group: "do", routes: [{ path: "/projects", element: ProjectsPage }], todayWidgets: [{ component: ProjectsWidget, slot: "right", order: 55 }], commands: [{ id: "projects.open", label: "Projeleri aç", run: () => navigate("/projects") }] });
