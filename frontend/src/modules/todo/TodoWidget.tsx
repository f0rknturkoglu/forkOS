import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Empty, Panel } from "@/core/ui";
import type { Todo } from "@/core/types";
import { navigate } from "@/app/router";

export function TodoWidget() {
  const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1); tomorrow.setHours(23, 59, 59, 999);
  const { data: todos = [] } = useQuery({ queryKey: ["todos", "today"],
    queryFn: () => api.get<Todo[]>(`/todos?due_before=${encodeURIComponent(tomorrow.toISOString())}&limit=7`) });
  const visible = todos.filter((todo) => ["open", "doing"].includes(todo.status)).slice(0, 7);
  return <Panel title="Bugünün görevleri" action={<button onClick={() => navigate("/todos")}
    className="text-meta text-muted hover:text-primary">tümünü aç →</button>}>
    {visible.length === 0 ? <Empty>Bugüne kalan görev yok.</Empty> : <ul className="space-y-2">
      {visible.map((todo) => <li key={todo.id} className="flex items-center gap-2 text-body">
        <span className="h-2 w-2 rounded-full bg-accent" /><span className="truncate">{todo.title}</span>
        <span className="ml-auto text-[10.5px] text-muted">p{todo.priority}</span></li>)}</ul>}
  </Panel>;
}
