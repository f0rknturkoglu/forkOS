import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, streamGoalStudio } from "@/core/api";
import { Button, Field, Input, Textarea, Select } from "@/core/ui";
import { invalidateAfter } from "@/core/invalidation";
import { entityRoute, typeLabel } from "@/core/entityRegistry";
import { readStored, writeStored } from "@/core/storage";
import type { components } from "@/generated/api-schema";

type S = components["schemas"];
type Session = S["StudioSessionOut"];
type Proposal = S["StudioProposal-Output"];
type AssistanceContext = NonNullable<S["StudioSessionIn"]["context"]>;
const operationNames: Record<string, string> = {
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
}: {
  goalId: string | null;
  goals: { id: string; title: string }[];
  onClose: () => void;
  assistanceContext?: AssistanceContext;
  initialMessage?: string;
}) {
  const storageKey = assistanceContext
    ? "assistance.session." + JSON.stringify(assistanceContext)
    : "goalStudio.session";
  const [context, setContext] = useState(goalId ?? "");
  const [session, setSession] = useState<Session | null>(null);
  const [resume, setResume] = useState(() => readStored(storageKey) ?? "");
  const [message, setMessage] = useState(initialMessage ?? "");
  const firstSent = useRef(false);
  const creationUuid = useRef(crypto.randomUUID());
  const [pendingTurn, setPendingTurn] = useState<{ client_uuid: string; message: string } | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [editorDirty, setEditorDirty] = useState(false);
  const [live, setLive] = useState("");
  const [error, setError] = useState("");
  const status = useQuery({
    queryKey: ["goal-studio-status"],
    queryFn: () => api.get<S["StudioStatus"]>("/goals/studio/status"),
    retry: false,
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
    if (next.state === "applied") invalidateAfter("goal.write");
  };
  const mutation = useMutation({
    mutationFn: (fn: () => Promise<Session>) => fn(),
    onSuccess: adopt,
    onError: (e: Error) => setError(e.message),
  });
  const run = (fn: () => Promise<Session>) => {
    setError("");
    mutation.mutate(fn);
  };
  const running = session?.state === "running";
  const busy = mutation.isPending || running || session?.state === "unknown_delivery";
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
  const send = () => {
    if (!message.trim() || status.data?.state !== "ready") return;
    const turn = { client_uuid: crypto.randomUUID(), message: message.trim() };
    setError("");
    mutation.mutate(async () => {
      const current =
        session ??
        (await api.post<Session>("/goals/studio/sessions", {
          client_uuid: creationUuid.current,
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
  return (
    <section
      aria-label={assistanceContext ? "Bağlam hakkında görüşme" : "Hermes Goal Studio"}
      className="min-w-0 rounded-card border border-subtle bg-surface p-4 stack-y-4"
    >
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="flex-1 text-heading">
          {assistanceContext ? "Bunun hakkında konuş" : "Hermes ile hedef hazırla"}
        </h2>
        <Button onClick={onClose}>Kapat</Button>
      </div>
      <p role="status" className="text-meta text-secondary">
        {status.data?.message ??
          (status.isError
            ? "Hermes durumu alınamadı; yerel özet ve normal işlemleri kullanabilirsin."
            : "Bağlantı kontrol ediliyor…")}
      </p>
      {status.data?.state !== "ready" && (
        <Button disabled={status.isFetching} onClick={() => void status.refetch()}>
          Bağlantıyı yeniden kontrol et
        </Button>
      )}
      <details className="text-meta text-muted">
        <summary>Bağlam ve gizlilik</summary>
        <p>
          {status.data?.provider_notice} Yalnız seçili bağlamın sınırlı kaynak özeti ve yazdığın mesajlar iletilir.
          Hafıza adayları ve günlük gövdeleri otomatik gönderilmez. Sohbet onay sayılmaz.
        </p>
      </details>
      {!session && !initialMessage && (
        <div className="flex flex-wrap items-end gap-2">
          {!assistanceContext && (
            <Field label="Görüşme bağlamı">
              <Select value={context} onChange={setContext}>
                <option value="">Yeni hedef</option>
                {goals.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.title}
                  </option>
                ))}
              </Select>
            </Field>
          )}
          <Button
            disabled={mutation.isPending}
            onClick={() =>
              run(() =>
                api.post<Session>("/goals/studio/sessions", {
                  client_uuid: creationUuid.current,
                  ...(assistanceContext ? { context: assistanceContext } : { goal_id: context || null }),
                }),
              )
            }
          >
            Görüşme aç
          </Button>
          {resume && (
            <Button
              disabled={mutation.isPending}
              onClick={() => run(() => api.get<Session>(`/goals/studio/sessions/${resume}`))}
            >
              Son görüşmeye dön
            </Button>
          )}
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
          <Input ariaLabel="Hermes mesajı" value={message} onChange={setMessage} className="min-w-0 flex-1" />
          <Button type="submit" disabled={mutation.isPending || status.data?.state !== "ready" || !message.trim()}>
            Hermes’e gönder
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
                <p className="text-meta text-muted">
                  {m.role === "user" ? "Sen · kullanıcı beyanı" : "Hermes · öneri"}
                </p>
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
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
            className="stack-y-2"
          >
            <Field
              label={
                assistanceContext
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
            <Button type="submit" disabled={busy || status.data?.state !== "ready" || !message.trim()}>
              Hermes’e gönder
            </Button>
          </form>
          {!assistanceContext && proposal && session.revision && (
            <div className="border-t border-subtle pt-4 stack-y-3">
              <h3 className="text-heading">Taslak · {session.revision.id.slice(0, 8)}</h3>
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
              {proposal.operations.map((op, index) => (
                <div key={op.key} className="rounded-card border border-subtle p-3 stack-y-2">
                  <p className="text-meta">
                    {operationNames[op.type]} · {op.key}
                  </p>
                  <Field label="Önerilen başlık">
                    <Input
                      ariaLabel={`Taslak başlık ${index + 1}`}
                      value={op.data.title ?? ""}
                      disabled={busy || session.state === "applied"}
                      onChange={(value) => changeTitle(index, value)}
                    />
                  </Field>
                  <details className="text-meta">
                    <summary>Önce / Sonra ve tüm alanlar</summary>
                    <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all">
                      {JSON.stringify(
                        {
                          before:
                            "target_id" in op && op.target_id ? (session.revision?.before[op.target_id] ?? null) : null,
                          after: op.data,
                        },
                        null,
                        2,
                      )}
                    </pre>
                  </details>
                </div>
              ))}
              <details>
                <summary className="text-meta">Gelişmiş taslak düzenleme (JSON)</summary>
                <ProposalEditor
                  proposal={proposal}
                  onChange={setProposal}
                  onDirty={setEditorDirty}
                  disabled={busy || session.state === "applied"}
                />
              </details>
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
                      run(() => api.put<Session>(`/goals/studio/sessions/${session.id}/proposal`, proposal))
                    }
                  >
                    Değişiklikleri doğrula · yeni revizyon
                  </Button>
                  <Button
                    disabled={busy || dirty || session.revision.state !== "ready_for_review"}
                    onClick={() =>
                      run(() =>
                        api.post<Session>(`/goals/studio/sessions/${session.id}/decision`, {
                          revision_id: session.revision!.id,
                          fingerprint: session.revision!.fingerprint,
                          decision: "approve",
                        }),
                      )
                    }
                  >
                    Bu revizyonu onayla ve uygula
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
                      <a className="text-accent underline" href={`#${entityRoute(type, String(id.id))}`}>
                        {typeLabel(type)} · {op?.data.title ?? key}
                      </a>
                    </p>
                  );
                })}
            </div>
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
