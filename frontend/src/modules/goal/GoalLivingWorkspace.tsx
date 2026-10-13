import { RelatedPanel } from "@/core/RelatedPanel";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { entityRoute, typeLabel } from "@/core/entityRegistry";
import { Button, Disclosure, Field, Input, Select, Textarea } from "@/core/ui";
import { GoalRoadmap, type RoadmapNode } from "./GoalRoadmap";
import { GoalPackagePreview } from "./GoalPackagePreview";
import type { components } from "@/generated/api-schema";
import { localDateKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";

type S = components["schemas"];
type Session = S["StudioSessionOut"];
type Snapshot = S["GoalContextSnapshot"];

export function GoalLivingWorkspace({
  goalId,
  title,
  nodeId,
  onProgress,
}: {
  goalId: string;
  title: string;
  nodeId?: string | null;
  onProgress?: (percent: number | null, counts: { completed: number; total: number }) => void;
}) {
  const [node, setNode] = useState<RoadmapNode | null>(null);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [parent, setParent] = useState("");
  const [review, setReview] = useState<Session | null>(null);
  const [error, setError] = useState("");
  const online = useOnline();
  const inspector = useRef<HTMLElement>(null);
  const graph = useQuery({
    queryKey: ["goal-roadmap", goalId],
    queryFn: () => api.get<S["RoadmapOut"]>(`/goals/${goalId}/roadmap`),
  });
  const context = useQuery({
    queryKey: ["goal-workspace", goalId],
    queryFn: () => api.get<Snapshot>(`/goals/${goalId}/workspace`),
  });
  useEffect(() => {
    if (graph.data) {
      onProgress?.(graph.data.percent ?? null, {
        completed: graph.data.completed_scope_count ?? 0,
        total: graph.data.scope_count ?? 0,
      });
      if (nodeId) {
        const found = graph.data.nodes.find((n) => n.id === nodeId);
        if (found) {
          setNode(found);
          setName(found.title);
          setDescription(found.description ?? "");
          setParent(found.parent_id ?? "");
        }
      }
    }
  }, [graph.data, nodeId, onProgress]);
  useEffect(() => {
    if (!node) return;
    inspector.current?.focus();
    inspector.current?.scrollIntoView({ block: "nearest", behavior: "instant" });
  }, [node?.id]);
  const mutation = useMutation({
    mutationFn: (fn: () => Promise<Session>) => fn(),
    onSuccess: (next) => {
      setReview(next);
      if (next.state === "applied") {
        invalidateAfter("goal-package.write");
        setEditing(false);
      }
      setError("");
    },
    onError: (e: Error) => setError(e.message),
  });
  const select = (n: RoadmapNode) => {
    setNode(n);
    setEditing(false);
    setReview(null);
    setName(n.title);
    setDescription(n.description ?? "");
    setParent(n.parent_id ?? "");
  };
  const linkTo = (type: string, id: string, label: string) => (
    <a className="text-accent underline break-words" href={`#${entityRoute(type, id).replace(/^#/, "")}`}>
      {label}
    </a>
  );
  return (
    <div className="stack-y-4">
      {graph.isPending && <p role="status">Yol haritası yükleniyor…</p>}
      {graph.isError && (
        <div role="alert">
          Yol haritası alınamadı. <Button onClick={() => void graph.refetch()}>Yeniden dene</Button>
        </div>
      )}
      {graph.data && <GoalRoadmap graph={graph.data} title={title} selected={node?.id ?? null} onSelect={select} />}
      {node && (
        <section
          ref={inspector}
          tabIndex={-1}
          onKeyDown={(event) => {
            if (event.key === "Escape") setNode(null);
          }}
          className="rounded-card border border-subtle p-4 stack-y-3"
          aria-label="Adım ayrıntıları"
        >
          <div className="flex flex-wrap justify-between gap-2">
            <h3 className="text-heading font-semibold break-words">{node.title}</h3>
            <Button size="sm" variant="ghost" onClick={() => setNode(null)}>
              Ayrıntıları kapat
            </Button>
          </div>
          {node.description && <p className="text-body text-secondary whitespace-pre-wrap">{node.description}</p>}
          {node.target_title && node.target_title !== node.title && (
            <p className="text-meta text-secondary">Bağlı kayıt: {node.target_title}</p>
          )}
          {node.canonical_percent != null && (
            <p className="text-meta text-secondary">Bağlı kaydın kendi ilerlemesi: %{node.canonical_percent}</p>
          )}
          <p className="text-meta text-secondary">
            {node.percent == null
              ? "Bu adımın tamamlanma kanıtı henüz yok."
              : `Bu hedefteki çalışma ilerlemesi: %${node.percent}`}
            {node.completion_gate ? " · Sonuç doğrulaması da gerekli" : ""}
          </p>
          {node.target_id &&
            node.target_type &&
            !node.missing &&
            linkTo(node.target_type, node.target_id, `${typeLabel(node.target_type)} içinde aç`)}
          {node.missing && (
            <p role="status" className="text-meta text-warn">
              Bağlı kayıt taşınmış, silinmiş veya arşivlenmiş olabilir. İlerleme bilinmiyor.
            </p>
          )}
          <Disclosure summary="Bu adımın bağlantıları">
            <RelatedPanel entityId={node.id} exclude={["roadmap_requires", "targets"]} />
          </Disclosure>
          {graph.data && node.persisted && (
            <Button size="sm" disabled={!online} onClick={() => setEditing(!editing)} ariaExpanded={editing}>
              Bu adımı düzenle
            </Button>
          )}
          {editing && (
            <div className="stack-y-2">
              <Field label="Adım adı">
                <Input ariaLabel="Yol haritası adım adı" value={name} onChange={setName} />
              </Field>
              <Field label="Açıklama">
                <Textarea ariaLabel="Yol haritası açıklaması" value={description} onChange={setDescription} />
              </Field>
              <Select ariaLabel="Üst aşama" value={parent} onChange={setParent}>
                <option value="">Hedefin altında</option>
                {(graph.data?.nodes ?? [])
                  .filter((n) => n.id !== node.id && ["phase", "period", "milestone"].includes(n.kind))
                  .map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.title}
                    </option>
                  ))}
              </Select>
              <Button
                disabled={!online || mutation.isPending || !name.trim()}
                onClick={() =>
                  mutation.mutate(async () => {
                    const started = await api.post<Session>("/goals/studio/sessions", {
                      client_uuid: crypto.randomUUID(),
                      goal_id: goalId,
                      mode: "living",
                    });
                    return api.put<Session>(`/goals/studio/sessions/${started.id}/proposal`, {
                      schema_version: 2,
                      rationale: "Yol haritası adımı düzenlemesi",
                      operations: [
                        {
                          key: "node_edit",
                          type: "roadmap.update",
                          target_id: node.id,
                          parent_ref: parent || null,
                          data: {
                            title: name,
                            description: description || null,
                            kind: node.kind,
                            position: node.position,
                            weight: node.weight,
                            progress_bearing: node.progress_bearing,
                            completion_gate: node.completion_gate,
                          },
                        },
                      ],
                    });
                  })
                }
              >
                Değişikliği incele
              </Button>
              <Button
                variant="ghost"
                disabled={!online || mutation.isPending}
                onClick={() =>
                  mutation.mutate(async () => {
                    const started = await api.post<Session>("/goals/studio/sessions", {
                      client_uuid: crypto.randomUUID(),
                      goal_id: goalId,
                      mode: "living",
                    });
                    return api.put<Session>(`/goals/studio/sessions/${started.id}/proposal`, {
                      schema_version: 2,
                      rationale: "Yol haritasından adım çıkarma",
                      operations: [
                        {
                          key: "node_detach",
                          type: "roadmap.update",
                          target_id: node.id,
                          parent_ref: node.parent_id ?? null,
                          detached: true,
                          data: {
                            title: node.title,
                            description: node.description,
                            kind: node.kind,
                            position: node.position,
                            weight: node.weight,
                            progress_bearing: node.progress_bearing,
                            completion_gate: node.completion_gate,
                          },
                        },
                      ],
                    });
                  })
                }
              >
                Haritadan çıkarma önerisini incele
              </Button>
              <p className="text-meta text-muted">Haritadan çıkarıldığında görev ve öğrenme kayıtları korunur.</p>
            </div>
          )}
          {review?.revision && (
            <div className="border-t border-subtle pt-3 stack-y-3">
              <GoalPackagePreview
                proposal={review.revision.proposal}
                before={review.revision.before}
                disabled
                onChange={() => undefined}
              />
              <p role="status" className="text-meta">
                {review.state === "applied"
                  ? "Değişiklik uygulandı."
                  : (review.revision.error ?? "Bu değişiklik onayını bekliyor.")}
              </p>
              {review.revision.state === "ready_for_review" && (
                <Button
                  variant="primary"
                  disabled={!online || mutation.isPending}
                  onClick={() =>
                    mutation.mutate(() =>
                      api.post<Session>(`/goals/studio/sessions/${review.id}/decision`, {
                        revision_id: review.revision!.id,
                        fingerprint: review.revision!.fingerprint,
                        decision: "approve",
                      }),
                    )
                  }
                >
                  Değişikliği onayla ve uygula
                </Button>
              )}
            </div>
          )}
          {error && (
            <p role="alert" className="text-danger text-meta">
              {error}
            </p>
          )}
        </section>
      )}
      {context.isPending && (
        <p className="text-meta" role="status">
          Bağlı çalışmalar yükleniyor…
        </p>
      )}
      {context.isError && (
        <p role="alert">
          Bağlı çalışmalar alınamadı. <Button onClick={() => void context.refetch()}>Yeniden dene</Button>
        </p>
      )}
      {context.data && (
        <div className="grid gap-3 sm:grid-cols-2">
          <section className="rounded-card border border-subtle p-4 stack-y-2">
            <h3 className="text-heading">Sıradaki işler</h3>
            {context.data.todos
              .filter((t) => t.status !== "done")
              .slice(0, 6)
              .map((t) => (
                <p key={t.id}>{linkTo("todo", t.id, t.title)}</p>
              ))}
            {!context.data.todos.some((t) => t.status !== "done") && (
              <p className="text-meta text-muted">Bekleyen görev yok. Sonraki aşamayı Hermes ile planlayabilirsin.</p>
            )}
          </section>
          <section className="rounded-card border border-subtle p-4 stack-y-2">
            <h3 className="text-heading">Yaklaşan çalışma planı</h3>
            {context.data.planned_slots
              .filter((s) => s.day >= localDateKey(new Date()))
              .sort((a, b) => a.day.localeCompare(b.day) || (a.start_min ?? 0) - (b.start_min ?? 0))
              .slice(0, 6)
              .map((s) => (
                <p key={s.id} className="text-meta">
                  {s.day} · {s.duration_min ?? "?"} dk ·{" "}
                  {linkTo("todo", s.entity_id, context.data.todos.find((t) => t.id === s.entity_id)?.title ?? "Görev")}
                </p>
              ))}
            <a className="text-accent underline text-meta" href="#/calendar">
              Takvimi aç
            </a>
            <a className="ml-3 text-accent underline text-meta" href="#/planner">
              Haftalık planı aç
            </a>
          </section>
          <section className="rounded-card border border-subtle p-4 stack-y-2">
            <h3 className="text-heading">Öğrenme</h3>
            {context.data.learning.slice(0, 8).map((t) => (
              <p key={t.id}>
                {linkTo("study_topic", t.id, t.title)}{" "}
                <span className="text-meta text-muted">{t.status === "done" ? "· Öğrenildi" : ""}</span>
              </p>
            ))}
            <Disclosure summary="Kaynaklar">
              {context.data.resources.map((r) => (
                <p key={r.id}>
                  {linkTo("learning_resource", r.id, r.title)}{" "}
                  <span className="text-meta text-muted">
                    ·{" "}
                    {r.missing_source
                      ? "Bağlı kaynak bulunamıyor"
                      : r.pending_need
                        ? "Kaynak ihtiyacı"
                        : r.has_url
                          ? "Bağlantılı kaynak"
                          : "Yerel kaynak"}
                  </span>
                </p>
              ))}
            </Disclosure>
          </section>
          <section className="rounded-card border border-subtle p-4 stack-y-2">
            <h3 className="text-heading">Projeler ve hareketler</h3>
            {context.data.projects.map((p) => (
              <p key={p.id}>
                {linkTo("project", p.id, p.title)} · {p.percent == null ? "İlerleme bilinmiyor" : `%${p.percent}`}
              </p>
            ))}
            <p className="text-meta text-secondary">
              Son 7 gün: {context.data.activity_windows["7"]?.completed_todos ?? 0} görev tamamlandı.
            </p>
            <Disclosure summary="30 ve 90 günlük hareketler">
              <p className="text-meta">
                30 gün: {context.data.activity_windows["30"]?.count ?? 0} hareket · 90 gün:{" "}
                {context.data.activity_windows["90"]?.count ?? 0} hareket. Hareket sayısı, gerçek sonuç ölçümü değildir.
              </p>
            </Disclosure>
          </section>
        </div>
      )}
    </div>
  );
}
