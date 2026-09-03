import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Repeat } from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { api, qs } from "@/core/api";
import { RelatedPanel } from "@/core/RelatedPanel";
import { Empty, PageFrame, PageHeader, RowList, Section, Toolbar, cx, SkeletonRows } from "@/core/ui";
import type { TagCount, Todo } from "@/core/types";
import { TodoComposer } from "./TodoComposer";
import { TodoRow } from "./TodoRow";
import { dueLabel, planLabel } from "./priority";
import { todayKey, tomorrowKey } from "@/lib/date";

const FILTERS = [
  { value: "open", label: "açık" },
  { value: "doing", label: "devam" },
  { value: "done", label: "tamam" },
  { value: "dropped", label: "bırakılan" },
  { value: "", label: "tümü" },
] as const;

/** Acik gorevleri zamana gore bolumler -- duz bir liste onceligi gizliyor. */
function bucketOf(todo: Todo): "overdue" | "today" | "soon" | "someday" {
  const due = dueLabel(todo.due_at);
  if (!due) return "someday";
  if (due.tone === "danger") return "overdue";
  if (due.tone === "accent") return "today";
  return "soon";
}

const BUCKETS = [
  { id: "overdue", label: "Gecikmiş" },
  { id: "today", label: "Bugün" },
  { id: "soon", label: "Yaklaşan" },
  { id: "someday", label: "Tarihsiz" },
] as const;

export function TodoPage() {
  const { path, params } = useHashRoute();
  // Kayit defteri rotasi (?focus={id}): secili gorevin iliskileri (Faz 18).
  const focusId = params.get("focus") ?? "";
  // Focus rotasi tamamlanmis/birakilmis bir goreve de gelebilir; o durumda
  // varsayilan "acik" filtresi hedef satiri saklamasin.
  const [status, setStatus] = useState<string>(focusId ? "" : "open");
  const [tag, setTag] = useState<string>("");
  const [routineOnly, setRoutineOnly] = useState(path === "/habits");

  // ?project=<id> filtre kipi: yalniz o projenin gorevleri listelenir.
  const projectFilter = params.get("project") ?? "";
  // ?planned=today filtre kipi: bugune (veya yarina) planlanmis gorevler.
  // Plan ile due_at ayni sey degil; bu filtre plan_slot'a bakar.
  const plannedFilter = params.get("planned") === "today";

  useEffect(() => {
    if (focusId) setStatus("");
  }, [focusId]);

  const { data: todos = [], isLoading } = useQuery({
    queryKey: ["todos", status, routineOnly ? "routines" : "all", projectFilter, plannedFilter],
    queryFn: () =>
      api.get<Todo[]>(
        `/todos${qs({
          status: status || undefined,
          limit: 300,
          recur_only: routineOnly || undefined,
        })}`,
      ),
  });
  const { data: tags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: () => api.get<TagCount[]>("/tags"),
  });

  let filtered = tag ? todos.filter((todo) => todo.tags.includes(tag)) : todos;
  if (projectFilter) filtered = filtered.filter((todo) => todo.project_id === projectFilter);
  if (plannedFilter) {
    // Gun anahtarlari app tz'den (Faz 14): tarayicinin UTC gunu degil.
    const today = todayKey();
    const tomorrow = tomorrowKey();
    filtered = filtered.filter((todo) => todo.planned_day === today || todo.planned_day === tomorrow);
  }
  const projectTitle = todos.find((todo) => todo.project_id === projectFilter)?.project_title;
  // Alt gorevler kendi satirlarinda degil, ustlerinin altinda gorunur.
  const childrenOf = filtered.reduce<Record<string, Todo[]>>((acc, todo) => {
    if (todo.parent_id) (acc[todo.parent_id] ??= []).push(todo);
    return acc;
  }, {});
  const parentIds = new Set(filtered.map((todo) => todo.id));
  const visible = filtered.filter((todo) => !todo.parent_id || !parentIds.has(todo.parent_id));
  const grouped =
    status === "open"
      ? BUCKETS.map((bucket) => ({
          ...bucket,
          items: visible.filter((todo) => bucketOf(todo) === bucket.id),
        })).filter((bucket) => bucket.items.length > 0)
      : [{ id: "all", label: "", items: visible }];

  return (
    <PageFrame className="space-y-5">
      <PageHeader
        eyebrow="Planlama"
        title="Görevler"
        action={
          <a href="#/planner" className="text-meta text-accent hover:underline">
            Haftalık plan →
          </a>
        }
      />

      <TodoComposer />

      <Toolbar>
        <div className="flex gap-1 overflow-x-auto">
          {FILTERS.map((item) => (
            <button
              key={item.value || "all"}
              type="button"
              onClick={() => setStatus(item.value)}
              aria-pressed={status === item.value}
              className={cx(
                "shrink-0 rounded-control border px-3 py-1.5 text-meta transition",
                status === item.value
                  ? "border-strong bg-surface-sunken text-primary"
                  : "border-transparent text-muted hover:text-primary",
              )}
            >
              {item.label}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setRoutineOnly((value) => !value)}
            aria-pressed={routineOnly}
            className={cx(
              "ml-1 flex shrink-0 items-center gap-1.5 rounded-control border px-3 py-1.5 text-meta transition",
              routineOnly
                ? "border-accent-border bg-accent-surface text-accent"
                : "border-subtle text-muted hover:border-strong hover:text-primary",
            )}
          >
            <Repeat size={12} /> Rutinler
          </button>
          {projectFilter && (
            <button
              type="button"
              onClick={() => navigate(path)}
              title="Proje filtresini kaldır"
              className="ml-1 flex shrink-0 items-center gap-1.5 rounded-control border border-accent-border bg-accent-surface px-3 py-1.5 text-meta text-accent"
            >
              {projectTitle ?? projectFilter} ✕
            </button>
          )}
        </div>

        <span className="min-w-2 flex-1" />

        {tags.length > 0 && (
          <div className="flex items-center gap-1 overflow-x-auto">
            {tag && (
              <button
                type="button"
                onClick={() => setTag("")}
                className="shrink-0 rounded-control border border-accent-border bg-accent-surface px-2.5 py-1 text-meta text-accent"
              >
                #{tag} ✕
              </button>
            )}
            {!tag &&
              tags.slice(0, 6).map((item) => (
                <button
                  key={item.name}
                  type="button"
                  onClick={() => setTag(item.name)}
                  className="shrink-0 rounded-control border border-subtle px-2.5 py-1 text-meta text-muted transition hover:border-strong hover:text-primary"
                >
                  #{item.name}
                </button>
              ))}
          </div>
        )}
      </Toolbar>

      {focusId && (
        <Section
          title="Bağlı kayıtlar"
          action={
            <button
              type="button"
              onClick={() => navigate(path)}
              className="text-meta text-muted hover:text-primary"
              aria-label="İlişkileri kapat"
            >
              ✕
            </button>
          }
        >
          <RelatedPanel entityId={focusId} />
        </Section>
      )}

      {isLoading ? (
        <SkeletonRows rows={8} />
      ) : visible.length === 0 ? (
        <Empty variant="page" title="Liste boş">
          {tag
            ? `#${tag} etiketli görev yok.`
            : routineOnly
              ? "Bu filtrede rutin görev yok. Bir göreve tekrar kuralı ekleyebilirsin."
              : "Bu filtrede görev yok. Yukarıdan ekleyebilirsin."}
        </Empty>
      ) : (
        grouped.map((bucket) => (
          <Section key={bucket.id} title={bucket.label || undefined} hint={`${bucket.items.length} görev`}>
            <RowList as="ul">
              {bucket.items.map((todo) => (
                <TodoRow key={todo.id} todo={todo} focused={todo.id === focusId}>
                  {(childrenOf[todo.id] ?? []).map((child) => (
                    <TodoRow key={child.id} todo={child} nested compact focused={child.id === focusId} />
                  ))}
                </TodoRow>
              ))}
            </RowList>
          </Section>
        ))
      )}
    </PageFrame>
  );
}
