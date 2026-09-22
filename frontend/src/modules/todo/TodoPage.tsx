import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Repeat } from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { api, qs } from "@/core/api";
import { RelatedPanel } from "@/core/RelatedPanel";
import { Empty, PageFrame, RowList, Section, SkeletonRows } from "@/core/ui";
import type { TagCount, Todo } from "@/core/types";
import { TodoComposer } from "./TodoComposer";
import { PlanViews } from "./PlanViews";
import { TodoRow } from "./TodoRow";
import { dueLabel, planLabel } from "./priority";
import { todayKey, tomorrowKey } from "@/lib/date";
import {
  Workspace,
  WorkspaceInspectorContent,
  WorkspacePaneHeader,
  WorkspaceRailButton,
  WorkspaceRailContent,
  WorkspaceRailGroup,
  WorkspaceScrollArea,
} from "@/core/workspace/Workspace";

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
  useEffect(() => setRoutineOnly(path === "/habits"), [path]);

  // ?project=<id> filtre kipi: yalniz o projenin gorevleri listelenir.
  const projectFilter = params.get("project") ?? "";
  // ?planned=today filtre kipi: bugune (veya yarina) planlanmis gorevler.
  // Plan ile due_at ayni sey degil; bu filtre plan_slot'a bakar.
  const plannedFilter = params.get("planned") === "today";

  useEffect(() => {
    if (focusId) setStatus("");
  }, [focusId]);

  /**
   * Kayitli gorunum uygulama yolu KALDIRILDI (Faz 26): durum/etiket/rutin
   * filtreleri rail'de yasar. Eski `?saved=<id>` baglantilari yalnizca
   * yok sayilir -- URL'de kalsa da sayfa normal acilir.
   */

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
    <PageFrame className="py-3">
      <Workspace
        rail={
          <WorkspaceRailContent>
            <WorkspaceRailGroup label="Durum">
              {FILTERS.map((item) => (
                <WorkspaceRailButton
                  key={item.value || "all"}
                  label={item.label}
                  active={status === item.value}
                  onClick={() => setStatus(item.value)}
                />
              ))}
            </WorkspaceRailGroup>
            <WorkspaceRailGroup label="Tür">
              <WorkspaceRailButton label="Tüm görevler" active={!routineOnly} onClick={() => setRoutineOnly(false)} />
              <WorkspaceRailButton
                label="Rutinler"
                active={routineOnly}
                icon={<Repeat size={13} />}
                onClick={() => setRoutineOnly(true)}
              />
            </WorkspaceRailGroup>
            {tags.length > 0 ? (
              <WorkspaceRailGroup label="Etiketler" hint={tags.length}>
                {tag ? (
                  <WorkspaceRailButton label={`#${tag}`} active onClick={() => setTag("")} />
                ) : (
                  tags
                    .slice(0, 12)
                    .map((item) => (
                      <WorkspaceRailButton
                        key={item.name}
                        label={`#${item.name}`}
                        count={item.count}
                        onClick={() => setTag(item.name)}
                      />
                    ))
                )}
              </WorkspaceRailGroup>
            ) : null}
          </WorkspaceRailContent>
        }
        inspector={
          focusId ? (
            <WorkspaceInspectorContent title="Görev bağlantıları">
              <RelatedPanel entityId={focusId} />
            </WorkspaceInspectorContent>
          ) : undefined
        }
      >
        <WorkspacePaneHeader
          eyebrow={routineOnly ? "Rutinler" : "Görevler"}
          title={
            projectFilter ? (projectTitle ?? "Proje görevleri") : routineOnly ? "Tekrarlanan görevler" : "Tüm görevler"
          }
          hint={`${visible.length} kayıt`}
          action={
            <a href="#/planner" className="text-meta text-accent hover:underline">
              Haftalık plan →
            </a>
          }
        >
          {projectFilter || plannedFilter ? (
            <p className="flex items-center gap-2 text-meta text-muted">
              {projectFilter ? (
                <>
                  <span>Yalnız “{projectTitle ?? projectFilter}” projesinin görevleri</span>
                  <button type="button" onClick={() => navigate(path)} className="text-accent hover:underline">
                    temizle
                  </button>
                </>
              ) : (
                <span>Bugün ve yarın planlananlar</span>
              )}
            </p>
          ) : null}
        </WorkspacePaneHeader>
        <PlanViews view={path === "/habits" ? "routines" : "tasks"} />
        <div className="border-b border-subtle bg-surface-sunken p-3">
          <TodoComposer defaultRecurring={path === "/habits"} />
        </div>
        <WorkspaceScrollArea className="space-y-3 p-3">
          {isLoading ? (
            <SkeletonRows rows={8} />
          ) : visible.length === 0 ? (
            <Empty variant="page" title="Liste boş">
              {tag ? `#${tag} etiketli görev yok.` : "Bu filtrede görev yok — yukarıdan ekleyebilirsin."}
            </Empty>
          ) : (
            grouped.map((bucket) => (
              <Section flat key={bucket.id} title={bucket.label || undefined} hint={`${bucket.items.length} görev`}>
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
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
