import { invalidateAfter } from "@/core/invalidation";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { api } from "@/core/api";
import { createTask } from "@/core/tasks";
import { Button, Empty, Input, RowList, Section, Select, cx, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { Project, Todo } from "@/core/types";
import { TodoRow } from "@/modules/todo/TodoRow";

export function createProjectTodo(projectId: string, title: string, milestoneId: string) {
  return createTask({
    title,
    project_id: projectId,
    ...(milestoneId ? { milestone_id: milestoneId } : {}),
  });
}

/**
 * Projenin gorevleri. Ayni `TodoRow` kullanilir -- tamamlama, silme,
 * baslik duzenleme her yerde ayni davranir.
 */
export function ProjectTodos({ project }: { project: Project }) {
  const [title, setTitle] = useState("");
  const [milestone, setMilestone] = useState("");
  const online = useOnline();
  const toast = useToast();

  const { data: todos = [] } = useQuery({
    queryKey: ["project-todos", project.id],
    queryFn: () => api.get<Todo[]>(`/projects/${project.id}/todos`),
  });

  // Bugun paneli de "todos" anahtarini izler -- projeden gorev ekleyince
  // oranin listesi de aninda tazelensin.
  const refresh = () => invalidateAfter("todo.write", "project.write");

  const add = useMutation({
    mutationFn: () => createProjectTodo(project.id, title, milestone),
    onSuccess: () => {
      setTitle("");
      refresh();
    },
    onError: () => toast.push("Görev eklenemedi.", { tone: "danger" }),
  });

  const milestones = (project.milestones ?? []).filter((item) => !item.completed_at);
  const open = todos.filter((todo) => todo.status !== "done");
  const done = todos.filter((todo) => todo.status === "done");

  // Acik gorevler kilometre tasina gore gruplanir; bagsizlar en sonda.
  const groups = [
    ...(project.milestones ?? [])
      .map((item) => ({
        id: item.id,
        label: item.title,
        done: Boolean(item.completed_at),
        items: open.filter((todo) => todo.milestone_id === item.id),
      }))
      .filter((group) => group.items.length > 0),
    {
      id: "loose",
      label: "Kilometre taşına bağlı değil",
      done: false,
      items: open.filter((todo) => !todo.milestone_id),
    },
  ].filter((group) => group.items.length > 0);

  return (
    <Section title="Görevler" hint={`${open.length} açık${done.length ? ` · ${done.length} bitti` : ""}`}>
      <form
        className="mb-3 flex flex-wrap gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (title.trim()) add.mutate();
        }}
      >
        <Input
          value={title}
          onChange={setTitle}
          placeholder="Bu projede ne yapılacak?"
          className="min-w-40 flex-1"
          ariaLabel="Yeni görev"
        />
        {milestones.length > 0 && (
          <Select value={milestone} onChange={setMilestone} className="w-44" ariaLabel="Kilometre taşı">
            <option value="">kilometre taşı yok</option>
            {milestones.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title}
              </option>
            ))}
          </Select>
        )}
        <Button type="submit" variant="primary" size="sm" disabled={!online || !title.trim() || add.isPending}>
          <Plus size={13} /> Ekle
        </Button>
      </form>

      {todos.length === 0 ? (
        <Empty>Bu projeye bağlı görev yok. GitHub issue'larından da oluşturabilirsin.</Empty>
      ) : (
        <>
          {groups.map((group) => (
            <div key={group.id} className="mb-3 last:mb-0">
              {groups.length > 1 && (
                <p className={cx("mb-1 label-caps", group.done && "line-through")}>{group.label}</p>
              )}
              <RowList as="ul">
                {group.items.map((todo) => (
                  <TodoRow key={todo.id} todo={todo} compact onChange={refresh} />
                ))}
              </RowList>
            </div>
          ))}
          {done.length > 0 && (
            <div className="mt-3 border-t border-subtle pt-2">
              <p className="mb-1 label-caps">Bitenler</p>
              <RowList as="ul">
                {done.map((todo) => (
                  <TodoRow key={todo.id} todo={todo} compact onChange={refresh} />
                ))}
              </RowList>
            </div>
          )}
        </>
      )}
    </Section>
  );
}
