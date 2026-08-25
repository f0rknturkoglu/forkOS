import { useQuery } from "@tanstack/react-query";
import { FolderGit2 } from "lucide-react";
import { api } from "@/core/api";
import { Empty, RowList, Section, cx, relativeTime } from "@/core/ui";
import { navigate } from "@/app/router";
import type { Project, Todo } from "@/core/types";

/**
 * Bugun panelindeki aktif projeler.
 *
 * Gosterilen sey "proje listesi" degil, her projede KAC ACIK IS oldugu --
 * panelde bir projenin yer kaplamasinin tek sebebi budur.
 */
export function ProjectsWidget() {
  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects?status=active"),
  });
  // Gorevler zaten projesini tasiyor; ayri istek acmadan sayilar buradan.
  const { data: todos = [] } = useQuery({
    queryKey: ["todos", "open"],
    queryFn: () => api.get<Todo[]>("/todos?status=open&limit=300"),
  });

  const openByProject = todos.reduce<Record<string, number>>((acc, todo) => {
    if (todo.project_id) acc[todo.project_id] = (acc[todo.project_id] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <Section
      title="Projeler"
      hint={projects.length > 0 ? `${projects.length} aktif` : undefined}
      action={
        <button type="button" onClick={() => navigate("/projects")} className="text-meta text-muted hover:text-primary">
          tümü →
        </button>
      }
    >
      {projects.length === 0 ? (
        <Empty>Aktif proje yok.</Empty>
      ) : (
        <RowList as="ul">
          {projects.slice(0, 5).map((project) => {
            const open = openByProject[project.id] ?? 0;
            return (
              <li key={project.id}>
                <button
                  type="button"
                  onClick={() => navigate("/projects")}
                  className="group flex w-full items-center gap-2.5 py-2 text-left"
                >
                  <FolderGit2 size={13} className="shrink-0 text-icon" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-body text-primary transition-colors group-hover:text-accent">
                      {project.title}
                    </span>
                    <span className="block truncate text-meta text-muted">
                      {project.github_repo ?? "depo bağlı değil"}
                      {project.last_activity_at && ` · ${relativeTime(project.last_activity_at)}`}
                    </span>
                  </span>
                  <span className={cx("shrink-0 text-meta tabular-nums", open > 0 ? "text-secondary" : "text-muted")}>
                    {open > 0 ? `${open} iş` : "boş"}
                  </span>
                </button>
              </li>
            );
          })}
        </RowList>
      )}
    </Section>
  );
}
