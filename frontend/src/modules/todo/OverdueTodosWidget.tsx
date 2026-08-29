import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Chip, Empty, RowList, Section } from "@/core/ui";
import { daysBetween, localDateKey, todayKey } from "@/lib/date";
import type { Todo } from "@/core/types";

/** Geciken gorevler -- agenda bugunu gosterir, gecikmisler ayri uyari hak eder. */
export function OverdueTodosWidget() {
  const { data = [] } = useQuery({
    queryKey: ["todos", "overdue"],
    queryFn: () => api.get<Todo[]>("/todos?status=open&limit=200"),
  });
  // Gecikmis = due_at'in app gunu bugunun app gununden once (Faz 14).
  const today = todayKey();
  const overdue = data.filter((todo) => todo.due_at && localDateKey(new Date(todo.due_at)) < today).slice(0, 5);
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
              <Chip tone="danger">{daysBetween(localDateKey(new Date(todo.due_at!)), today)} gün</Chip>
            </div>
          ))}
        </RowList>
      )}
    </Section>
  );
}
