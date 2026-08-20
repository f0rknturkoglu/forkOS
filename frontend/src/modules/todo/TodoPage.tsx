import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Badge, Button, Empty, Panel, cx } from "@/core/ui";
import type { Todo } from "@/core/types";
import { useInvalidate, useOnline } from "@/lib/hooks";

const priorityLabel = ["yok", "dusuk", "orta", "yuksek"];

export function TodoPage() {
  const [status, setStatus] = useState<string>("open");
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState(2);
  const online = useOnline();
  const invalidate = useInvalidate();
  const { data: todos = [], isLoading } = useQuery({
    queryKey: ["todos", status],
    queryFn: () => api.get<Todo[]>(`/todos${qs({ status: status || undefined })}`),
  });
  const refresh = () => invalidate("todos", "activity", "review-preview");
  const create = useMutation({
    mutationFn: () => api.post<Todo>("/todos", { title, priority }),
    onSuccess: () => { setTitle(""); refresh(); },
  });
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: string; body: object }) =>
      api.patch<Todo>(`/todos/${id}`, body),
    onSuccess: refresh,
  });
  const complete = useMutation({
    mutationFn: (id: string) => api.post<Todo>(`/todos/${id}/complete`),
    onSuccess: refresh,
  });

  function edit(todo: Todo) {
    const next = prompt("Gorev", todo.title)?.trim();
    if (next && next !== todo.title) patch.mutate({ id: todo.id, body: { title: next } });
  }

  return (
    <div className="space-y-4 p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-xl font-semibold">Todo</h1>
          <p className="text-xs text-neutral-500">Yapilacaklar, alt gorevler ve oncelikler.</p></div>
        <a href="#/planner" className="text-xs text-sky-400 hover:underline">Weekly Planner →</a>
      </header>
      <Panel title="Hizli ekle">
        <form className="flex flex-wrap gap-2" onSubmit={(event) => {
          event.preventDefault();
          if (title.trim()) create.mutate();
        }}>
          <input value={title} onChange={(event) => setTitle(event.target.value)}
            placeholder="Ne yapilacak?" autoFocus
            className="min-w-64 flex-1 rounded border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm outline-none focus:border-sky-700" />
          <select value={priority} onChange={(event) => setPriority(Number(event.target.value))}
            className="rounded border border-neutral-700 bg-neutral-950 px-2 text-sm">
            {priorityLabel.map((label, value) => <option key={value} value={value}>{label}</option>)}
          </select>
          <Button type="submit" variant="primary" disabled={!online || !title.trim()}>ekle</Button>
        </form>
      </Panel>
      <div className="flex gap-1">
        {["open", "doing", "done", "dropped", ""].map((value) => (
          <Button key={value || "all"} variant={status === value ? "primary" : "ghost"}
            onClick={() => setStatus(value)}>{value || "tumu"}</Button>
        ))}
      </div>
      <Panel>
        {isLoading ? <p className="text-sm text-neutral-500">Yukleniyor...</p> : todos.length === 0 ?
          <Empty>Bu filtrede gorev yok.</Empty> : (
          <ul className="divide-y divide-neutral-800">
            {todos.map((todo) => (
              <li key={todo.id} className={cx("flex items-start gap-3 py-3", todo.parent_id && "ml-6")}>
                <button disabled={!online || todo.status === "done"}
                  onClick={() => complete.mutate(todo.id)}
                  className={cx("mt-0.5 h-4 w-4 rounded border", todo.status === "done"
                    ? "border-emerald-700 bg-emerald-800" : "border-neutral-600")}
                  aria-label="tamamla" />
                <div className="min-w-0 flex-1">
                  <button onClick={() => edit(todo)} className={cx("text-left text-sm",
                    todo.status === "done" && "text-neutral-600 line-through")}>{todo.title}</button>
                  <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-neutral-600">
                    <span>p{todo.priority} · {priorityLabel[todo.priority]}</span>
                    {todo.due_at && <span>{new Date(todo.due_at).toLocaleString("tr-TR")}</span>}
                    {todo.parent_id && <Badge>alt gorev</Badge>}
                  </div>
                </div>
                {todo.status === "open" && <Button disabled={!online}
                  onClick={() => patch.mutate({ id: todo.id, body: { status: "doing" } })}>basla</Button>}
                {!['done', 'dropped'].includes(todo.status) && <Button disabled={!online}
                  onClick={() => patch.mutate({ id: todo.id, body: { status: "dropped" } })}>birak</Button>}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
