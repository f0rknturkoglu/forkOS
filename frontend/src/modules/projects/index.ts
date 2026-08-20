import { navigate } from "@/app/router";
import { registerModule } from "@/core/registry";
import { ProjectsPage } from "./ProjectsPage";

registerModule({ id: "projects", title: "Projects", searchLabel: "Projects", routes: [{ path: "/projects", element: ProjectsPage }], commands: [{ id: "projects.open", label: "Projeleri aç", run: () => navigate("/projects") }] });
