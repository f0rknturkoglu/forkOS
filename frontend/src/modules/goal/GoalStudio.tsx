import { GoalPackagePreview } from "./GoalPackagePreview";
import { ArrowUp, RefreshCw, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, streamGoalStudio } from "@/core/api";
import { Button, Disclosure, IconButton, Field, Input, Textarea, Select, Checkbox } from "@/core/ui";
import { invalidateAfter } from "@/core/invalidation";
import { entityRoute, typeLabel } from "@/core/entityRegistry";
import { appLocalToUtc, localDateKey } from "@/lib/date";
import { readStored, writeStored } from "@/core/storage";
import type { components } from "@/generated/api-schema";

type S = components["schemas"];
type Session = S["StudioSessionOut"];
type Proposal = S["StudioProposal-Output"];
type AssistanceContext = NonNullable<S["StudioSessionIn"]["context"]>;
const operationNames: Record<string, string> = {
  "roadmap.create": "Yol haritası adımı",
  "roadmap.update": "Adımı düzenle",
  "learning.area": "Öğrenme alanı",
  "learning.topic": "Öğrenme konusu",
  "learning.resource": "Kaynak ihtiyacı",
  "todo.create": "Görev",
  "plan.schedule": "Çalışma bloğu",
  "record.link": "Mevcut kayıt bağlantısı",
  "plan.create": "Plan oluştur",
  "pillar.create": "Stratejik alan oluştur",
  "goal.create": "Hedef oluştur",
  "goal.update": "Hedefi düzenle",
  "key_result.save": "Ölçülebilir sonuç",
  "milestone.create": "Hedef adımı oluştur",
  "milestone.update": "Hedef adımını düzenle",
};
const stateNames: Record<string, string> = {
  drafting: "Görüşme",
  running: "Hermes yanıtlıyor…",
  unknown_delivery: "Teslim sonucu belirsiz",
  delivery_blocked: "Gönderim engellendi",
  approval_pending: "Onay bekliyor",
  applied: "Uygulandı",
  rejected: "Reddedildi",
  stale: "Bağlam değişti",
  failed: "İşlem tamamlanamadı",
};

export function GoalStudio({
  goalId,
  goals,
  onClose,
  assistanceContext,
  initialMessage,
  feedbackOnly = false,
  living = false,
  longTerm = false,
  onApplied,
}: {
  goalId: string | null;
  goals: { id: string; title: string }[];
  onClose: () => void;
  assistanceContext?: AssistanceContext;
  initialMessage?: string;
  feedbackOnly?: boolean;
  living?: boolean;
  longTerm?: boolean;
  onApplied?: (goalId: string) => void;
}) {
  const storageKey = assistanceContext
    ? "assistance.session." + JSON.stringify(assistanceContext)
    : goalId
      ? `goalStudio.${living ? "living" : feedbackOnly ? "feedback" : "draft"}.${goalId}`
      : living
        ? "goalStudio.living.session"
        : "goalStudio.session";
  const [context, setContext] = useState(goalId ?? "");
  const [session, setSession] = useState<Session | null>(null);
  const [resume, setResume] = useState(() => readStored(storageKey) ?? "");
  const [message, setMessage] = useState(initialMessage ?? "");
  const firstSent = useRef(false);
  const creationUuid = useRef(crypto.randomUUID());
  const [pendingTurn, setPendingTurn] = useState<{ client_uuid: string; message: string } | null>(null);
  const [proposal, setProposalState] = useState<Proposal | null>(null);
  const proposalRef = useRef<Proposal | null>(null);
  const setProposal = (next: Proposal | null | ((old: Proposal | null) => Proposal | null)) => {
    const value = typeof next === "function" ? next(proposalRef.current) : next;
    proposalRef.current = value;
    setProposalState(value);
  };
  const [editorDirty, setEditorDirty] = useState(false);
  const [live, setLive] = useState("");
  const [error, setError] = useState("");
  const [cloudChecked, setCloudChecked] = useState(false);
  const status = useQuery({
    queryKey: ["goal-studio-status"],
    queryFn: () => api.get<S["StudioStatus"]>("/goals/studio/status"),
    retry: false,
  });
  useEffect(() => setCloudChecked(false), [status.data?.consent?.policy_id]);
  const permission = useMutation({
    mutationFn: (allowed: boolean) =>
      api.put<S["StudioConsentOut"]>("/goals/studio/consent", {
        revision: status.data?.consent?.revision,
        policy_id: status.data?.consent?.policy_id,
        allowed,
      }),
    onSuccess: () => {
      setError("");
      setCloudChecked(false);
      invalidateAfter("goal-studio.consent");
      void status.refetch();
    },
    onError: (e: Error) => {
      setError(e.message);
      void status.refetch();
    },
  });
  const adopt = (next: Session) => {
    if (JSON.stringify(next.context ?? null) !== JSON.stringify(assistanceContext ?? null)) {
      setError("Bu görüşme farklı bir bağlama ait; yeni görüşme aç.");
      return;
    }
    setSession(next);
    setResume(next.id);
    writeStored(storageKey, next.id);
    setProposal(next.revision?.proposal ?? null);
    setEditorDirty(false);
    setPendingTurn(next.pending_turn ?? null);
    if (next.state === "applied") invalidateAfter("goal-package.write");
  };
  const mutation = useMutation({
    mutationFn: (fn: () => Promise<Session>) => fn(),
    onSuccess: adopt,
    onError: (e: Error) => {
      setError(e.message);
      void status.refetch();
    },
  });
  const run = (fn: () => Promise<Session>) => {
    setError("");
    mutation.mutate(fn);
  };
  const running = session?.state === "running";
  const busy =
    mutation.isPending || running || session?.state === "unknown_delivery" || session?.state === "delivery_blocked";
  const dirty = editorDirty || JSON.stringify(proposal) !== JSON.stringify(session?.revision?.proposal ?? null);
  useEffect(() => {
    if (!running || !session) return;
    const id = session.id,
      controller = new AbortController();
    let disposed = false,
      polling = false;
    setLive("");
    const reconcile = async () => {
      if (disposed || polling) return;
      polling = true;
      try {
        const next = await api.get<Session>(`/goals/studio/sessions/${id}`);
        if (!disposed) adopt(next);
      } catch (e) {
        if (!disposed) setError((e as Error).message);
      } finally {
        polling = false;
      }
    };
    void streamGoalStudio(id, controller.signal, (text) => setLive((old) => (old + text).slice(-20000)))
      .catch(() => undefined)
      .finally(() => void reconcile());
    const timer = setInterval(() => void reconcile(), 10000);
    return () => {
      disposed = true;
      controller.abort();
      clearInterval(timer);
    };
  }, [session?.id, running]);
  useEffect(() => {
    if (living && goalId && !resume && !session) {
      let cancelled = false;
      const latest = api.get<Session>(`/goals/${goalId}/conversation`);
      void latest
        .then((next) => {
          if (!cancelled) adopt(next);
        })
        .catch(() => undefined);
      return () => {
        cancelled = true;
      };
    }
  }, [living, goalId, resume, session?.id]);
  const send = () => {
    if (!message.trim() || status.data?.state !== "ready") return;
    const turn = { client_uuid: crypto.randomUUID(), message: message.trim() };
    setError("");
    mutation.mutate(async () => {
      const current =
        session ??
        (await api.post<Session>("/goals/studio/sessions", {
          client_uuid: creationUuid.current,
          ...(living ? { mode: "living", long_term: longTerm } : feedbackOnly ? { mode: "feedback" } : {}),
          ...(assistanceContext ? { context: assistanceContext } : { goal_id: context || null }),
        }));
      if (JSON.stringify(current.context ?? null) !== JSON.stringify(assistanceContext ?? null))
        throw new Error("Görüşme bağlamı değişti; yeniden aç.");
      adopt(current);
      setPendingTurn(turn);
      setMessage("");
      return api.post<Session>(`/goals/studio/sessions/${current.id}/turns`, turn);
    });
  };
  useEffect(() => {
    if (!initialMessage || firstSent.current || status.data?.state !== "ready") return;
    firstSent.current = true;
    send();
  }, [initialMessage, status.data?.state]);
  const changeTitle = (index: number, title: string) =>
    setProposal((old) =>
      old
        ? {
            ...old,
            operations: old.operations.map((op, i) =>
              i === index ? ({ ...op, data: { ...op.data, title } } as Proposal["operations"][number]) : op,
            ),
          }
        : null,
    );
  const changeField = (index: number, field: string, value: string | number | null) =>
    setProposal((old) =>
      old
        ? {
            ...old,
            operations: old.operations.map((op, i) =>
              i === index ? ({ ...op, data: { ...op.data, [field]: value } } as Proposal["operations"][number]) : op,
            ),
          }
        : null,
    );
  return (
    <section
      aria-label={
        feedbackOnly
          ? "Hermes ile ilerleme"
          : assistanceContext
            ? "Bağlam hakkında görüşme"
            : living
              ? "Hermes ile hedef planı"
              : "Hermes Goal Studio"
      }
      className="min-w-0 rounded-card border border-subtle bg-surface p-3 stack-y-2"
    >
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="flex-1 text-body font-medium">
          {feedbackOnly
            ? "Hermes ile ilerlemeni değerlendir"
            : assistanceContext
              ? "Hermes"
              : "Hermes ile hedef ve plan hazırla"}
        </h2>
        {!session && !assistanceContext && !goalId && goals.length > 0 && (
          <Select ariaLabel="Görüşme bağlamı" value={context} onChange={setContext}>
            <option value="">Yeni hedef</option>
            {goals.map((g) => (
              <option key={g.id} value={g.id}>
                {g.title}
              </option>
            ))}
          </Select>
        )}
        {resume && !session && (
          <Button
            size="sm"
            variant="ghost"
            disabled={mutation.isPending}
            onClick={() => run(() => api.get<Session>(`/goals/studio/sessions/${resume}`))}
          >
            Son görüşme
          </Button>
        )}
        <IconButton title="Kapat" onClick={onClose}>
          <X size={14} />
        </IconButton>
      </div>
      <Disclosure summary="Bağlantı ayrıntıları" className="text-meta text-muted">
        <div className="flex flex-wrap items-center gap-2 text-meta text-muted">
          {status.data?.provider_label && (
            <span>
              {status.data.provider_label} · {status.data.local ? "Yerel" : "Bulut"} · {status.data.configured_model}
            </span>
          )}
          {status.data?.state === "ready" && <span role="status">Bağlı</span>}
          <IconButton
            title="Bağlantıyı yeniden kontrol et"
            disabled={status.isFetching}
            onClick={() => void status.refetch()}
          >
            <RefreshCw size={14} />
          </IconButton>
        </div>
        {session?.runtime && (
          <p className="text-meta text-secondary">
            Son yanıt: {session.runtime.provider} · {session.runtime.model}
          </p>
        )}
      </Disclosure>
      {status.data?.local === false && status.data.consent && (
        <div className="rounded-control border border-subtle p-2 stack-y-2">
          <p className="text-meta">
            Seçili bağlam özeti ve mesajın {status.data.provider_label} sağlayıcısına gönderilir. Sağlayıcının veri
            saklama kuralları geçerlidir.
          </p>
          {status.data.consent.allowed ? (
            <div className="flex flex-wrap items-center gap-2 text-meta">
              <span>Bu sağlayıcı ve model için izin açık</span>
              <Button
                size="sm"
                variant="ghost"
                disabled={permission.isPending}
                onClick={() => permission.mutate(false)}
              >
                Bulut iznini geri al
              </Button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <Checkbox
                checked={cloudChecked}
                onChange={setCloudChecked}
                label="Bu sağlayıcı ve modelle Goal Studio görüşmelerine izin veriyorum"
              />
              <Button
                size="sm"
                disabled={!cloudChecked || permission.isPending}
                onClick={() => permission.mutate(true)}
              >
                İzni kaydet
              </Button>
            </div>
          )}
        </div>
      )}
      {status.data?.state !== "ready" && (
        <div className="flex items-center gap-2 text-meta text-muted">
          <span role="status" title={status.data?.message}>
            {status.isError
              ? "Hermes’e bağlanılamadı"
              : status.data?.state === "not_configured"
                ? "Hermes yapılandırılmamış"
                : (status.data?.message ?? "Bağlantı kontrol ediliyor…")}
          </span>
        </div>
      )}
      {error && (
        <p role="alert" className="text-meta text-danger">
          {error}
        </p>
      )}
      {!session && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
          className="flex flex-wrap gap-2"
        >
          <Input
            ariaLabel="Hermes mesajı"
            placeholder={
              feedbackOnly
                ? "İlerlemem nasıl? Sıradaki adımda neyi geliştirebilirim?"
                : "Ne başarmak istiyorsun? Örn. YDS 60+ ya da beş yıllık plan…"
            }
            value={message}
            onChange={setMessage}
            className="min-w-0 flex-1"
          />
          <Button
            type="submit"
            ariaLabel="Hermes’e gönder"
            disabled={mutation.isPending || status.data?.state !== "ready" || !message.trim()}
          >
            <img
              src="/brands/nous.png"
              alt=""
              aria-hidden="true"
              className="h-5 w-5 shrink-0 rounded-full object-contain"
            />
            <ArrowUp size={16} aria-hidden />
          </Button>
        </form>
      )}
      {error && session && pendingTurn && session.state !== "running" && (
        <Button
          disabled={mutation.isPending}
          onClick={() => run(() => api.post<Session>(`/goals/studio/sessions/${session.id}/turns`, pendingTurn))}
        >
          Gönderimi yeniden dene
        </Button>
      )}
      {session && (
        <>
          <div className="flex flex-wrap gap-2">
            <p role="status" className="flex-1 text-meta">
              {stateNames[session.state] ?? session.state}
            </p>
            <Button
              disabled={busy}
              onClick={() => {
                setSession(null);
                setProposal(null);
                creationUuid.current = crypto.randomUUID();
              }}
            >
              Yeni görüşme
            </Button>
            <Button
              disabled={mutation.isPending}
              onClick={() => run(() => api.get<Session>(`/goals/studio/sessions/${session.id}`))}
            >
              Durumu kontrol et
            </Button>
          </div>
          {session.error && (
            <p role="alert" className="text-meta text-warn">
              {session.error}
            </p>
          )}
          <div role="log" aria-label="Bağlam görüşmesi" className="max-h-80 overflow-y-auto stack-y-3">
            {session.messages.map((m, i) => (
              <div key={i} className="rounded-card bg-surface-sunken p-3">
                <p className="text-meta text-muted">{m.role === "user" ? "Sen" : "Hermes"}</p>
                <p className="whitespace-pre-wrap break-words text-body">{String(m.text ?? "")}</p>
              </div>
            ))}
          </div>
          {running && (
            <>
              <p aria-live="polite" className="max-h-48 overflow-y-auto whitespace-pre-wrap break-words text-meta">
                {live || "Yanıt hazırlanıyor…"}
              </p>
              <Button
                disabled={mutation.isPending}
                onClick={() => run(() => api.post<Session>(`/goals/studio/sessions/${session.id}/stop`))}
              >
                Turu durdur
              </Button>
            </>
          )}
          {session.state === "unknown_delivery" && pendingTurn && (
            <Button
              disabled={mutation.isPending}
              onClick={() => run(() => api.post<Session>(`/goals/studio/sessions/${session.id}/turns`, pendingTurn))}
            >
              Aynı turu uzlaştır
            </Button>
          )}
          {session.state === "delivery_blocked" && (
            <Button
              disabled={mutation.isPending}
              onClick={() => run(() => api.post<Session>(`/goals/studio/sessions/${session.id}/stop`))}
            >
              Engellenen turu kapat
            </Button>
          )}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
            className="stack-y-2"
          >
            <Field
              label={
                feedbackOnly
                  ? "İlerlemen hakkında neyi değerlendirelim?"
                  : assistanceContext
                    ? "Bu bağlam hakkında neyi değerlendirelim?"
                    : "Neyi başarmak istiyorsun? / Taslağı nasıl değiştirelim?"
              }
            >
              <Textarea
                ariaLabel="Hermes mesajı"
                value={message}
                rows={3}
                onChange={(value) => setMessage(value.slice(0, 6000))}
              />
            </Field>
            <Button
              type="submit"
              ariaLabel="Hermes’e gönder"
              disabled={busy || status.data?.state !== "ready" || !message.trim()}
            >
              <img
                src="/brands/nous.png"
                alt=""
                aria-hidden="true"
                className="h-5 w-5 shrink-0 rounded-full object-contain"
              />
              <ArrowUp size={16} aria-hidden />
            </Button>
          </form>
          {proposal && session.revision && (
            <Disclosure
              key={session.revision.state}
              summary={session.revision.state === "applied" ? "Uygulanan hedef planı" : "Hedef paketini incele"}
              defaultOpen={proposal.schema_version === 1 || session.revision.state !== "applied"}
            >
              <div className="border-t border-subtle pt-4 stack-y-3">
                <h3 className="text-heading">Taslak</h3>
                <p className="text-body">{proposal.rationale}</p>
                {[
                  ...(proposal.assumptions ?? []).map((x) => "Varsayım: " + x),
                  ...(proposal.missing_information ?? []).map((x) => "Bilinmiyor: " + x),
                  ...(proposal.warnings ?? []).map((x) => "Uyarı: " + x),
                ].map((x, i) => (
                  <p key={i} className="text-meta text-warn">
                    {x}
                  </p>
                ))}
                {proposal.schema_version === 2 ? (
                  <GoalPackagePreview
                    proposal={proposal}
                    before={session.revision.before}
                    onChange={setProposal}
                    disabled={busy || session.state === "applied"}
                  />
                ) : (
                  proposal.operations.map((op, index) => (
                    <div key={op.key} className="rounded-card border border-subtle p-3 stack-y-2">
                      <p className="text-meta">{operationNames[op.type]}</p>
                      <Field label="Önerilen başlık">
                        <Input
                          ariaLabel={`Taslak başlık ${index + 1}`}
                          value={"title" in op.data ? (op.data.title ?? "") : ""}
                          disabled={busy || session.state === "applied"}
                          onChange={(value) => changeTitle(index, value)}
                        />
                      </Field>
                      {(op.type === "goal.create" || op.type === "goal.update" || op.type === "plan.create") && (
                        <Field label={op.type === "plan.create" ? "Plan özeti" : "Çalışma programı ve açıklama"}>
                          <Textarea
                            ariaLabel={`Taslak açıklama ${index + 1}`}
                            value={(op.type === "plan.create" ? op.data.summary : op.data.description) ?? ""}
                            rows={3}
                            disabled={busy || session.state === "applied"}
                            onChange={(value) =>
                              changeField(index, op.type === "plan.create" ? "summary" : "description", value || null)
                            }
                          />
                        </Field>
                      )}
                      {(op.type === "goal.create" ||
                        op.type === "goal.update" ||
                        op.type === "milestone.create" ||
                        op.type === "milestone.update") && (
                        <Field label="Hedef tarihi">
                          <Input
                            type="date"
                            ariaLabel={`Taslak tarih ${index + 1}`}
                            value={(() => {
                              const value =
                                "target_at" in op.data
                                  ? op.data.target_at
                                  : "due_at" in op.data
                                    ? op.data.due_at
                                    : null;
                              return value ? localDateKey(new Date(value)) : "";
                            })()}
                            disabled={busy || session.state === "applied"}
                            onChange={(value) =>
                              changeField(
                                index,
                                op.type.startsWith("milestone.") ? "due_at" : "target_at",
                                value ? appLocalToUtc(value, 0, 0) : null,
                              )
                            }
                          />
                        </Field>
                      )}
                      {op.type === "key_result.save" && (
                        <div className="grid gap-2 sm:grid-cols-2">
                          <Field label="Hedef değer">
                            <Input
                              type="number"
                              ariaLabel={`Taslak hedef değer ${index + 1}`}
                              value={String(op.data.target_value)}
                              disabled={busy || session.state === "applied"}
                              onChange={(value) => changeField(index, "target_value", value)}
                            />
                          </Field>
                          <Field label="Birim">
                            <Input
                              ariaLabel={`Taslak birim ${index + 1}`}
                              value={op.data.unit ?? "adet"}
                              disabled={busy || session.state === "applied"}
                              onChange={(value) => changeField(index, "unit", value)}
                            />
                          </Field>
                        </div>
                      )}
                      <Disclosure className="text-meta" summary="Ayrıntılar">
                        <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all">
                          {JSON.stringify(
                            {
                              before:
                                "target_id" in op && op.target_id
                                  ? (session.revision?.before[op.target_id] ?? null)
                                  : null,
                              after: op.data,
                            },
                            null,
                            2,
                          )}
                        </pre>
                      </Disclosure>
                    </div>
                  ))
                )}
                <Disclosure summary="Gelişmiş taslak düzenleme (JSON)">
                  <ProposalEditor
                    proposal={proposal}
                    onChange={setProposal}
                    onDirty={setEditorDirty}
                    disabled={busy || session.state === "applied"}
                  />
                </Disclosure>
                {session.revision.error && (
                  <p role="alert" className="text-danger text-meta">
                    {session.revision.error}
                  </p>
                )}
                {session.state !== "applied" && (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      disabled={busy || !dirty}
                      onClick={() =>
                        run(() =>
                          api.put<Session>(`/goals/studio/sessions/${session.id}/proposal`, proposalRef.current),
                        )
                      }
                    >
                      Değişiklikleri kaydet
                    </Button>
                    <Button
                      disabled={busy || dirty || session.revision.state !== "ready_for_review"}
                      onClick={() =>
                        run(async () => {
                          const next = await api.post<Session>(`/goals/studio/sessions/${session.id}/decision`, {
                            revision_id: session.revision!.id,
                            fingerprint: session.revision!.fingerprint,
                            decision: "approve",
                          });
                          if (next.state === "applied" && next.goal_id) onApplied?.(next.goal_id);
                          return next;
                        })
                      }
                    >
                      Taslağı onayla ve uygula
                    </Button>
                    <Button
                      disabled={busy || dirty || session.revision.state !== "ready_for_review"}
                      onClick={() =>
                        run(() =>
                          api.post<Session>(`/goals/studio/sessions/${session.id}/decision`, {
                            revision_id: session.revision!.id,
                            fingerprint: session.revision!.fingerprint,
                            decision: "reject",
                          }),
                        )
                      }
                    >
                      Reddet
                    </Button>
                  </div>
                )}
                {dirty && (
                  <p role="status" className="text-meta text-warn">
                    Değiştirilmiş taslak onaylanamaz; önce yeni revizyonu doğrula.
                  </p>
                )}
                {session.state === "applied" &&
                  Object.entries(session.revision.results).map(([key, id]) => {
                    const op = proposal.operations.find((o) => o.key === key);
                    const type = id.type;
                    return (
                      <p key={key} className="text-body">
                        <a
                          className="text-accent underline"
                          href={`#${entityRoute(type, String(id.id)).replace(/^#/, "")}`}
                        >
                          {typeLabel(type)} · {op && "title" in op.data ? (op.data.title ?? key) : "Çalışma kaydı"}
                        </a>
                      </p>
                    );
                  })}
              </div>
            </Disclosure>
          )}
        </>
      )}
    </section>
  );
}
function ProposalEditor({
  proposal,
  onChange,
  disabled,
  onDirty,
}: {
  onDirty: (dirty: boolean) => void;
  proposal: Proposal;
  onChange: (p: Proposal) => void;
  disabled: boolean;
}) {
  const [text, setText] = useState(JSON.stringify(proposal, null, 2));
  const [error, setError] = useState("");
  useEffect(() => setText(JSON.stringify(proposal, null, 2)), [proposal]);
  return (
    <div className="stack-y-2">
      <Field label="Tüm öneri alanları">
        <Textarea
          ariaLabel="Taslak JSON"
          rows={10}
          value={text}
          disabled={disabled}
          onChange={(value) => {
            setText(value.slice(0, 60000));
            onDirty(value !== JSON.stringify(proposal, null, 2));
          }}
        />
      </Field>
      <Button
        disabled={disabled}
        onClick={() => {
          try {
            const p = JSON.parse(text);
            if (
              !Array.isArray(p.operations) ||
              !p.operations.length ||
              !p.operations.every(
                (op: { type?: string; data?: unknown }) => op.type && operationNames[op.type] && op.data,
              )
            )
              throw new Error();
            onChange(p as Proposal);
            onDirty(false);
            setError("");
          } catch {
            setError("Desteklenen işlemleri içeren geçerli JSON gerekli; sunucu tüm alanları tekrar doğrular.");
          }
        }}
      >
        Önizlemeye aktar
      </Button>
      {error && (
        <p role="alert" className="text-danger text-meta">
          {error}
        </p>
      )}
    </div>
  );
}
