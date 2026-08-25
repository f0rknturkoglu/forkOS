import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Chip, Empty, RowList, Section } from "@/core/ui";
import type { Todo } from "@/core/types";

/** Geciken gorevler -- agenda bugunu gosterir, gecikmisler ayri uyari hak eder. */
export function OverdueTodosWidget() {
  const { data = [] } = useQuery({
    queryKey: ["todos", "overdue"],
    queryFn: () => api.get<Todo[]>("/todos?status=open&limit=200"),
  });
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const overdue = data.filter((todo) => todo.due_at && new Date(todo.due_at) < today).slice(0, 5);
  return (
    <Section title="Geciken görevler">
      {overdue.length === 0 ? (
        <Empty>Geciken görev yok.</Empty>
      ) : (
        <RowList>
          {overdue.map((todo) => (
            <div key={todo.id} className="flex items-center gap-2 py-2 text-meta">
              <a
                href={`#/todos?focus=${todo.id}`}
                className="min-w-0 flex-1 truncate text-body text-primary hover:text-accent"
              >
                {todo.title}
              </a>
              <Chip tone="danger">
                {Math.ceil((today.getTime() - new Date(todo.due_at!).getTime()) / 86_400_000)} gün
              </Chip>
            </div>
          ))}
        </RowList>
      )}
    </Section>
  );
}
