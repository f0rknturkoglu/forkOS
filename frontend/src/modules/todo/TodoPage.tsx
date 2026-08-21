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
  /** Satir ici duzenlenen gorevin id'si. */
  const [editing, setEditing] = useState<string | null>(null);
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

  function rename(todo: Todo, next: string) {
    const value = next.trim();
    setEditing(null);
    if (value && value !== todo.title) patch.mutate({ id: todo.id, body: { title: value } });
  }

  return (
    <div className="space-y-4 p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-meta text-muted">Yapılacaklar, alt görevler ve öncelikler.</p></div>
        <a href="#/planner" className="text-meta text-accent hover:underline">Haftalık plan →</a>
      </header>
      <Panel title="Hızlı ekle">
        <form className="flex flex-wrap gap-2" onSubmit={(event) => {
          event.preventDefault();
          if (title.trim()) create.mutate();
        }}>
          <input value={title} onChange={(event) => setTitle(event.target.value)}
            placeholder="Ne yapilacak?" autoFocus
            className="min-w-64 flex-1 rounded border border-strong bg-canvas px-3 py-2 text-body outline-none focus:border-accent" />
          <select value={priority} onChange={(event) => setPriority(Number(event.target.value))}
            className="rounded border border-strong bg-canvas px-2 text-body">
            {priorityLabel.map((label, value) => <option key={value} value={value}>{label}</option>)}
          </select>
          <Button type="submit" variant="primary" disabled={!online || !title.trim()}>ekle</Button>
        </form>
      </Panel>
      <div className="flex gap-1">
        {["open", "doing", "done", "dropped", ""].map((value) => (
          <Button key={value || "all"} variant={status === value ? "primary" : "ghost"}
            onClick={() => setStatus(value)}>{value || "tümü"}</Button>
        ))}
      </div>
      <Panel>
        {isLoading ? <p className="text-body text-muted">Yükleniyor…</p> : todos.length === 0 ?
          <Empty>Bu filtrede görev yok.</Empty> : (
          <ul className="divide-y divide-subtle">
            {todos.map((todo) => (
              <li key={todo.id} className={cx("flex items-start gap-3 py-3", todo.parent_id && "ml-6")}>
                <button disabled={!online || todo.status === "done"}
                  onClick={() => complete.mutate(todo.id)}
                  className={cx("mt-0.5 h-4 w-4 rounded border", todo.status === "done"
                    ? "border-ok-border bg-ok" : "border-strong")}
                  aria-label="tamamla" />
                <div className="min-w-0 flex-1">
                  {editing === todo.id ? (
                    <form className="flex gap-2" onSubmit={(event) => {
                      event.preventDefault();
                      rename(todo, (new FormData(event.currentTarget).get("title") as string) ?? "");
                    }}>
                      <input name="title" autoFocus defaultValue={todo.title}
                        aria-label="Görev başlığı"
                        onKeyDown={(event) => { if (event.key === "Escape") setEditing(null); }}
                        className="h-8 min-w-0 flex-1 rounded-control border border-subtle bg-surface px-2 text-body text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent" />
                      <Button type="submit" variant="primary" size="sm">Kaydet</Button>
                      <Button size="sm" onClick={() => setEditing(null)}>Vazgeç</Button>
                    </form>
                  ) : (
                    <button disabled={!online} onClick={() => setEditing(todo.id)}
                      title="Başlığı düzenle"
                      className={cx("text-left text-body hover:text-accent",
                        todo.status === "done" && "text-muted line-through")}>{todo.title}</button>
                  )}
                  <div className="mt-1 flex flex-wrap gap-2 text-meta text-muted">
                    <span>p{todo.priority} · {priorityLabel[todo.priority]}</span>
                    {todo.due_at && <span>{new Date(todo.due_at).toLocaleString("tr-TR")}</span>}
                    {todo.parent_id && <Badge>alt görev</Badge>}
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
