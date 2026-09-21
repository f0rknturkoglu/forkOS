import { lazy } from "react";
import { Layers } from "lucide-react";
import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { ProjectsWidget } from "./ProjectsWidget";

const ProjectsPage = lazy(() => import("./ProjectsPage").then((module) => ({ default: module.ProjectsPage })));

registerModule({
  id: "projects",
  title: "Projeler",
  description: "Projelerini aşamalara böl, ilerleme ve durumlarını tek yerden yönet.",
  icon: Layers,
  routes: [{ path: "/projects", element: ProjectsPage }],
  todayWidgets: [
    {
      id: "projects.widget",
      title: "Projeler",
      component: ProjectsWidget,
      slot: "right",
      order: 55,
      defaultVisible: false,
    },
  ],
  commands: [{ id: "projects.open", label: "Projeleri aç", run: () => navigate("/projects") }],
});
