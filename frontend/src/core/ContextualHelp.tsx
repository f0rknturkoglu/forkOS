import { Suspense, lazy, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { readStored, writeStored, removeStored } from "@/core/storage";
import {
  confirmSemanticCandidate,
  promoteSemanticCandidate,
  rejectSemanticCandidate,
  getSemanticCandidate,
} from "@/core/agentSemantic";
import type { SemanticCandidate } from "@/core/agentSemantic";
const GoalStudio = lazy(() => import("@/modules/goal/GoalStudio").then((module) => ({ default: module.GoalStudio })));
const PlanReviewModal = lazy(() =>
  import("@/modules/today/PendingDecisions").then((module) => ({ default: module.PlanReviewModal })),
);
import type { ExecutionPlanView } from "@/core/execution";
import { Button, Checkbox, Field, Input, Modal, Section, SkeletonRows, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { localDateKey } from "@/lib/date";
import type { components } from "@/generated/api-schema";

type S = components["schemas"];
export type AssistanceContext = NonNullable<S["StudioSessionIn"]["context"]>;

function tomorrow() {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  return localDateKey(date);
}

/** Local summary is visible; Hermes is contacted only after an explicit message. */
export function ContextualHelp({ context, label }: { context: AssistanceContext; label: string }) {
  const [message, setMessage] = useState("");
  const [chat, setChat] = useState<string | null>(null);
  const [summary, setSummary] = useState(true);
  const online = useOnline();
  return (
    <div className="min-w-0 stack-y-3">
      {summary ? (
        <ContextSummary key={JSON.stringify(context)} context={context} onClose={() => setSummary(false)} />
      ) : (
        <Button size="sm" onClick={() => setSummary(true)}>
          {label}
        </Button>
      )}
      {chat === null ? (
        <form
          className="flex min-w-0 items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (message.trim() && online) setChat(message.trim());
          }}
        >
          <Input
            ariaLabel="Hermes'e sor"
            placeholder="Hermes’e sor…"
            value={message}
            onChange={(value) => setMessage(value.slice(0, 6000))}
            className="min-w-0 flex-1"
          />
          <Button type="submit" disabled={!online || !message.trim()}>
            Gönder
          </Button>
        </form>
      ) : (
        <Suspense fallback={<SkeletonRows rows={2} />}>
          <GoalStudio
            goalId={null}
            goals={[]}
            assistanceContext={context}
            initialMessage={chat}
            onClose={() => {
              setChat(null);
              setMessage("");
            }}
          />
        </Suspense>
      )}
    </div>
  );
}

function ContextSummary({ context, onClose }: { context: AssistanceContext; onClose: () => void }) {
  const query = useQuery({
    queryKey: [
      {
        review: "review-preview",
        project: "projects",
        goal: "strategy-overview",
        career: "opportunity",
        learning: "study-topic",
        planning: "todos",
      }[context.kind],
      "contextual-summary",
      context,
    ],
    queryFn: () => api.post<S["AssistanceSummary"]>("/goals/studio/context", context),
    staleTime: 60_000,
    retry: false,
  });
  const data = query.data;
  return (
    <Section title={data?.title ?? "Mevcut durum"} action={<Button onClick={onClose}>Kapat</Button>}>
      {query.isPending ? (
        <SkeletonRows rows={3} />
      ) : query.isError ? (
        <div role="alert" className="stack-y-2 text-meta text-danger">
          <p>Özet alınamadı. Normal işlemleri kullanmaya devam edebilirsin.</p>
          <Button onClick={() => void query.refetch()}>Yeniden dene</Button>
        </div>
      ) : (
        data && (
          <div className="min-w-0 stack-y-3">
            <p className="text-meta text-muted">
              Yerel kayıt özeti · {new Date(data.generated_at).toLocaleString("tr-TR")}
            </p>
            {data.coverage && (
              <p className="text-meta text-secondary">
                {data.coverage.partial
                  ? "Dönem / kaynak penceresi tamamlanmadı; tam dönem karşılaştırması yapılmaz."
                  : "Seçilen dönemin kayıtları."}
              </p>
            )}
            <ul className="list-inside list-disc stack-y-2 text-body">
              {(data.facts ?? []).slice(0, 3).map((fact, i) => (
                <li key={i} className="break-words">
                  {fact.status === "candidate"
                    ? "Kayıtlı beyan / öneri: "
                    : fact.status === "missing"
                      ? "Bilinmiyor: "
                      : ""}
                  {fact.text}
                  {(fact.support_refs ?? []).length > 0 && (
                    <span className="sr-only"> Kaynak mevcut; kanıt ayrıntılarında.</span>
                  )}
                </li>
              ))}
            </ul>
            {(data.facts ?? []).length > 3 && (
              <details className="text-meta">
                <summary>Özetin tamamı</summary>
                <ul className="mt-2 stack-y-2">
                  {(data.facts ?? []).slice(3).map((fact, i) => (
                    <li key={i}>{fact.text}</li>
                  ))}
                </ul>
              </details>
            )}
            {(data.warnings ?? []).length > 0 && (
              <details className="text-meta text-warn">
                <summary>Kaynak sınırları ve eksikler ({(data.warnings ?? []).length})</summary>
                <ul className="mt-2 stack-y-1">
                  {(data.warnings ?? []).map((warning, i) => (
                    <li key={i}>{warning}</li>
                  ))}
                </ul>
              </details>
            )}
            {(data.links ?? []).length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                {(data.links ?? []).slice(0, 3).map((link) => (
                  <a
                    key={link.id}
                    className="rounded-control border border-subtle px-2 py-1 text-meta text-accent"
                    href={`#${link.route}`}
                  >
                    {context.kind === "project" && link.schedulable ? `Buradan devam et · ${link.title}` : link.title}
                  </a>
                ))}
                {(data.links ?? []).some((link) => link.schedulable) && (
                  <ScheduleTasks
                    tasks={(data.links ?? []).filter((link) => link.schedulable)}
                    label="Seçili görevleri planla"
                  />
                )}
              </div>
            )}
            <details className="text-meta text-secondary">
              <summary>Kanıt ve kaynaklar</summary>
              <ul className="mt-2 stack-y-2">
                {(data.sources ?? []).map((source) => (
                  <li key={source.ref} className="break-words">
                    {source.title ?? source.kind} ·{" "}
                    {source.timestamp ? new Date(source.timestamp).toLocaleString("tr-TR") : "Zaman belirtilmemiş"}
                    <span className="block text-micro text-muted">{source.ref}</span>
                    {source.entity_id && (data.links ?? []).some((link) => link.id === source.entity_id) && (
                      <a
                        className="text-accent underline"
                        href={`#${(data.links ?? []).find((link) => link.id === source.entity_id)?.route ?? ""}`}
                      >
                        Kaydı aç
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </details>
            <ContextMemory candidates={data.memory_candidates ?? []} sources={data.sources ?? []} />
          </div>
        )
      )}
    </Section>
  );
}

/** Same existing candidates and promotion engine. Dismissal persists without generating new candidates. */
export function ContextMemory({
  candidates,
  sources = [],
}: {
  candidates: SemanticCandidate[];
  sources?: S["SourceRef"][];
}) {
  const [dismissed, setDismissed] = useState<string[]>(() => {
    try {
      return (() => {
        const raw: unknown = JSON.parse(readStored("memory.dismissed") ?? "[]");
        return Array.isArray(raw) ? raw.filter((id): id is string => typeof id === "string") : [];
      })();
    } catch {
      return [];
    }
  });
  const [selected, setSelected] = useState<SemanticCandidate | null>(null);
  const [error, setError] = useState("");
  const online = useOnline();
  const toast = useToast();
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const dismiss = (id: string) => {
    const next = [...new Set([...dismissed, id])];
    setDismissed(next);
    writeStored("memory.dismissed", JSON.stringify(next));
    setSelected(null);
  };
  const decide = useMutation({
    mutationFn: async (kind: "remember" | "reject") => {
      if (!selected) throw new Error("Aday seçilmedi");
      if (kind === "reject") return rejectSemanticCandidate(selected.id, selected.revision);
      const confirmed = await confirmSemanticCandidate(selected.id, selected.revision);
      setSelected(confirmed);
      return promoteSemanticCandidate(confirmed.id, confirmed.revision, confirmed.suggested_destination);
    },
    onSuccess: (result) => {
      invalidateAfter("agent-semantic.write");
      if ("status" in result && !["promoted", "already_promoted", "rejected"].includes(result.status)) {
        setError("Aday onaylandı; kalıcı kayıt tamamlanmadı. Ayarlardan inceleyebilirsin.");
        return;
      }
      toast.push("status" in result ? "Kalıcı bilgi kaydedildi" : "Aday reddedildi", { tone: "ok" });
      if (selected) dismiss(selected.id);
    },
    onError: (e: Error) => {
      setError(e.message + " · Son durumu yeniden oku; onay kalıcı kaydın tamamlandığı anlamına gelmez.");
      setNeedsRefresh(true);
      invalidateAfter("agent-semantic.write");
    },
  });
  const visible = candidates.filter((candidate) => !dismissed.includes(candidate.id));
  if (!visible.length) return null;
  return (
    <div className="border-t border-subtle pt-3 stack-y-2">
      <p className="text-meta text-secondary">
        Bu çalışma tercihini / kararı sonraki planlarda hatırlamamı ister misin?
      </p>
      {visible.map((candidate) => (
        <div key={candidate.id} className="flex flex-wrap items-center gap-2">
          <span className="min-w-0 flex-1 text-body">{candidate.statement}</span>
          <Button
            size="sm"
            onClick={() => {
              setSelected(candidate);
              setError("");
              setNeedsRefresh(false);
            }}
          >
            İncele
          </Button>
          <Button size="sm" variant="ghost" onClick={() => dismiss(candidate.id)}>
            Şimdi değil
          </Button>
        </div>
      ))}
      {selected && (
        <Modal open title="Hatırlanacak bilgi" onClose={() => setSelected(null)}>
          <div className="stack-y-3">
            <p className="text-body">{selected.statement}</p>
            <p className="text-meta text-muted">
              Henüz kalıcı bilgi değil. Kapsam:{" "}
              {selected.scope_project ? "Seçili proje" : selected.scope === "global" ? "Genel tercih" : "Oturum"}.
              Hedef:{" "}
              {selected.suggested_destination === "hot_memory" ? "Güncel çalışma hafızası" : "Obsidian kalıcı bilgi"}.
            </p>
            <ul className="text-meta stack-y-1">
              {(selected.evidence_refs ?? []).map((ref, i) => {
                const source = sources.find((source) => source.ref === ref.ref);
                return (
                  <li key={i} className="break-words">
                    {source?.title ?? String(ref.ref ?? "Kaynak")}
                    {source && <span className="text-muted"> · {source.ref}</span>}
                    {source?.timestamp && (
                      <span className="text-muted"> · {new Date(source.timestamp).toLocaleString("tr-TR")}</span>
                    )}
                  </li>
                );
              })}
            </ul>
            {error && (
              <p role="alert" className="text-meta text-danger">
                {error}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              {needsRefresh && (
                <Button
                  disabled={!online || decide.isPending}
                  onClick={() => {
                    if (selected)
                      void getSemanticCandidate(selected.id)
                        .then((current) => {
                          if (["promoted", "rejected"].includes(current.status)) {
                            dismiss(current.id);
                            toast.push(
                              current.status === "promoted" ? "Kalıcı bilgi kaydedilmiş" : "Aday reddedilmiş",
                              { tone: "ok" },
                            );
                          } else {
                            setSelected(current);
                            setNeedsRefresh(false);
                            setError("Güncel kayıt alındı; kapsamı ve kanıtı yeniden incele.");
                          }
                        })
                        .catch((e: Error) => setError(e.message));
                  }}
                >
                  Son durumu oku
                </Button>
              )}
              <Button disabled={!online || decide.isPending || needsRefresh} onClick={() => decide.mutate("remember")}>
                Hatırla
              </Button>
              <Button disabled={!online || decide.isPending || needsRefresh} onClick={() => decide.mutate("reject")}>
                Reddet
              </Button>
              <Button disabled={decide.isPending} onClick={() => dismiss(selected.id)}>
                Şimdi değil
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

export function ScheduleTasks({
  tasks,
  label = "Planla",
  defaultDay,
}: {
  tasks: { id: string; title: string }[];
  label?: string;
  defaultDay?: string;
}) {
  const [open, setOpen] = useState(false);
  const [ids, setIds] = useState<string[]>([]);
  const [day, setDay] = useState(defaultDay ?? tomorrow());
  const [planId, setPlanId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const online = useOnline();
  const prepare = useMutation({
    mutationFn: () => {
      const key = "planning.request." + JSON.stringify({ todo_ids: [...ids].sort(), day });
      const identity = readStored(key) ?? crypto.randomUUID();
      writeStored(key, identity); // Durable before HTTP; lost response retries the original plan identity.
      return api.post<ExecutionPlanView>("/execution/planning", { client_uuid: identity, todo_ids: ids, day });
    },
    onSuccess: (plan) => {
      invalidateAfter("execution.write");
      setPlanId(plan.plan_row_id);
      setError("");
    },
    onError: (e: Error) => setError(e.message),
  });
  return (
    <>
      <Button
        size="sm"
        onClick={() => {
          setOpen(true);
          setIds(tasks.slice(0, 10).map((task) => task.id));
          setPlanId(null);
        }}
      >
        {label}
      </Button>
      {open && planId === null && (
        <Modal open onClose={() => setOpen(false)} title="Plan değişikliğini hazırla">
          <div className="stack-y-3">
            <p className="text-meta text-muted">
              Yalnız seçilen görevlerin plan günü değişir. Son tarih değişmez; saat ve süre korunur. Uygulamadan önce
              tam değişiklikleri inceleyeceksin.
            </p>
            {tasks.slice(0, 10).map((task) => (
              <Checkbox
                key={task.id}
                label={task.title}
                checked={ids.includes(task.id)}
                disabled={prepare.isPending}
                onChange={(checked) =>
                  setIds((old) => (checked ? [...old, task.id] : old.filter((id) => id !== task.id)))
                }
              />
            ))}
            {tasks.length > 10 && (
              <p className="text-meta text-warn">Bir planda en fazla 10 görev; diğerleri normal planlayıcıda.</p>
            )}
            <Field label="Plan günü">
              <Input
                type="date"
                ariaLabel="Plan günü"
                value={day}
                disabled={prepare.isPending}
                onChange={setDay}
                onBlur={setDay}
              />
            </Field>
            {error && (
              <p role="alert" className="text-meta text-danger">
                {error}
              </p>
            )}
            <Button disabled={!online || prepare.isPending || !ids.length || !day} onClick={() => prepare.mutate()}>
              {prepare.isPending ? "Hazırlanıyor…" : "Değişiklikleri incele"}
            </Button>
          </div>
        </Modal>
      )}
      {open && planId !== null && (
        <Suspense fallback={<SkeletonRows rows={2} />}>
          <PlanReviewModal
            planRowId={planId}
            applyTogether
            onReprepare={() => {
              removeStored("planning.request." + JSON.stringify({ todo_ids: [...ids].sort(), day }));
              setPlanId(null);
              setError("");
            }}
            onClose={() => setOpen(false)}
          />
        </Suspense>
      )}
    </>
  );
}
