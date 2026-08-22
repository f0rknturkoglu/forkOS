import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { api } from "@/core/api";
import { Empty, RowList, Section } from "@/core/ui";
import type { Todo } from "@/core/types";
import { navigate } from "@/app/router";
import { TodoComposer } from "./TodoComposer";
import { TodoRow } from "./TodoRow";

/**
 * Bugun panelindeki gorev listesi. Satirlar CANLI: buradan tamamlanir,
 * silinir, baslik duzeltilir.
 *
 * Bugun tamamlananlar listeden DUSMEZ, altta ustu cizili birikir -- gun
 * icinde "ne yaptim, ne kaldi" sorusunu tek bakista cevaplasin diye.
 */
export function TodoWidget() {
  const [adding, setAdding] = useState(false);

  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(23, 59, 59, 999);
  const midnight = new Date();
  midnight.setHours(0, 0, 0, 0);

  // include_undated: tarihsiz gorev de bugunun listesine dussun.
  // completed_after: bugun bitenler de gelsin (asagida gosterilecek).
  const { data: todos = [] } = useQuery({
    queryKey: ["todos", "today"],
    queryFn: () => api.get<Todo[]>(
      `/todos?due_before=${encodeURIComponent(tomorrow.toISOString())}`
      + `&include_undated=true&completed_after=${encodeURIComponent(midnight.toISOString())}`
      + "&limit=40"),
  });

  const open = todos.filter((todo) => ["open", "doing"].includes(todo.status)).slice(0, 8);
  const done = todos
    .filter((todo) => todo.status === "done" && todo.completed_at)
    .sort((a, b) => (b.completed_at ?? "").localeCompare(a.completed_at ?? ""));

  return (
    <Section
      title="Bugünün görevleri"
      hint={done.length > 0 ? `${done.length} bitti` : undefined}
      action={
        <span className="flex items-center gap-3">
          <button type="button" onClick={() => setAdding((v) => !v)}
            className="flex items-center gap-1 text-meta text-accent hover:underline">
            <Plus size={13} /> {adding ? "kapat" : "ekle"}
          </button>
          <button type="button" onClick={() => navigate("/todos")}
            className="text-meta text-muted hover:text-primary">tümü →</button>
        </span>
      }
    >
      {adding && (
        <div className="mb-3">
          <TodoComposer onCreated={() => setAdding(false)} />
        </div>
      )}

      {open.length === 0 && done.length === 0 ? (
        <Empty>Bugüne kalan görev yok.</Empty>
      ) : (
        <>
          {open.length > 0 && (
            <RowList as="ul">
              {open.map((todo) => <TodoRow key={todo.id} todo={todo} compact />)}
            </RowList>
          )}

          {open.length === 0 && (
            <p className="py-2 text-meta text-ok">Bugünkü her şey bitti.</p>
          )}

          {done.length > 0 && (
            <div className="mt-3 border-t border-subtle pt-2">
              <p className="mb-1 label-caps">Bugün bitenler</p>
              <RowList as="ul">
                {done.map((todo) => <TodoRow key={todo.id} todo={todo} compact />)}
              </RowList>
            </div>
          )}
        </>
      )}
    </Section>
  );
}
