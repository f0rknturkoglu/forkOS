import { Layers } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { ProjectsPage } from "./ProjectsPage";
import { ProjectsWidget } from "./ProjectsWidget";

registerModule({ id: "projects", title: "Projeler", icon: Layers, group: "do", searchLabel: "Projects", routes: [{ path: "/projects", element: ProjectsPage }], todayWidgets: [{ component: ProjectsWidget, zone: "rhythm", slot: "right", order: 55 }], commands: [{ id: "projects.open", label: "Projeleri aç", run: () => navigate("/projects") }] });
