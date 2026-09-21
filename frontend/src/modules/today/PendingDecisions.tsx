import { useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, ListChecks, PencilLine, ShieldCheck } from "lucide-react";
import {
  PLAN_STATE_LABELS,
  approveExecutionPlan,
  canTransition,
  cancelExecutionPlan,
  fetchExecutionPlan,
  pendingExecutionPlans,
  rejectExecutionPlan,
  respondExecutionPlan,
  runExecutionPlan,
} from "@/core/execution";
import type { ExecutionPlanState, ExecutionPlanView, ExecutionStepView } from "@/core/execution";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Chip, Field, Input, Modal, RowList, Section, SkeletonRows, relativeTime } from "@/core/ui";

/**
 * "Bekleyen kararlar" — Hermes'in hazirladigi, KARARI KULLANICIYA ait planlar.
 *
 * Uc sey ayni ekranda: planin ne yapacagi (adimlar + kanit), ne kadar baglayici
 * oldugu (adim/mutasyon sayisi + son gecerlilik) ve karar. Onay SUNUCU
 * tarafinda bir kayittir ve tam olarak bu REVIZYONA baglanir; bu yuzden
 * approve/execute cagrilari revizyonu acikca gonderir ve onaydan sonra plan
 * bekleyen listesinden cikar.
 *
 * Plan icerigi burada DUZENLENEMEZ: revizyon immutable'dir. "Düzenle" dugmesi
 * de bu yuzden bir form degil, Hermes'e yeni revizyon hazirlatma yonergesidir
 * (bkz. docs/hermes/h7-execution.md).
 *
 * Bos liste hicbir sey cizmez: karar yuzeyi gunun akisina gurultu eklemez.
 */

/** Plan durumu -> rozet tonu. */
const STATE_TONE: Record<ExecutionPlanState, "neutral" | "accent" | "ok" | "warn" | "danger"> = {
  draft: "neutral",
  input_required: "warn",
  awaiting_approval: "warn",
  approved: "accent",
  executing: "accent",
  completed: "ok",
  partial: "warn",
  failed: "danger",
  rejected: "neutral",
  cancelled: "neutral",
  expired: "neutral",
};

/** Makbuz durumu -> rozet tonu (`STEP_STATUSES`). */
const RECEIPT_TONE: Record<string, "neutral" | "accent" | "ok" | "warn" | "danger"> = {
  completed: "ok",
  failed: "danger",
  skipped: "neutral",
  not_attempted: "warn",
};

/**
 * Plan eylemi -> yurutme sonrasi tazelenecek canonical yuzey. Eylem adlari
 * KAPALI H1 kumesindendir (`app/integrations/agent/write_registry.py`), bu
 * yuzden esleme tamdir: `execute` gercek mutasyonu H1 uzerinden yapar ve
 * dokundugu paneller tazelenmezse ekran bayat kalir.
 */
const ACTION_SURFACE: Record<
  string,
  "todo.write" | "project.write" | "opportunity.write" | "bookmark.write" | "obsidian.write"
> = {
  todo_create: "todo.write",
  todo_update: "todo.write",
  todo_complete: "todo.write",
  todo_plan: "todo.write",
  project_update: "project.write",
  opportunity_transition: "opportunity.write",
  application_transition: "opportunity.write",
  bookmark_capture: "bookmark.write",
  bookmark_update: "bookmark.write",
  // Bilgi notlari Vault'ta yasar: canonical tabloya satir yazilmaz (§46).
  brain_capture: "obsidian.write",
  brain_save_to_entity: "obsidian.write",
};

/** Karar cagrilari: hangi ucun gidecegini ve baglamini tek yerde tutar. */
type Decision =
  | { kind: "approve"; revision: string }
  | { kind: "reject" }
  | { kind: "cancel" }
  | { kind: "respond"; answers: Record<string, string> }
  | { kind: "execute"; revision: string; actions: string[] };

export function PendingDecisions() {
  const [openRowId, setOpenRowId] = useState<number | null>(null);
  const { data: plans = [] } = useQuery({
    queryKey: ["execution-plans"],
    queryFn: pendingExecutionPlans,
    // TTL sunucuda uygulanir (`expire_due_plans`): suresi dolan plan listeden
    // dusmeli, yoksa kullanici yurutulemeyecek bir plana karar verir.
    refetchInterval: 60_000,
  });

  // Bos liste = bolum yok. Inceleme modali LISTEDEN bagimsiz yasar: onaydan
  // sonra plan bekleyen listesinden cikar ama ayni revizyon yurutulmeye devam
  // edilir; modal listeyle birlikte kaybolursa kullanici yarida kalir.
  if (plans.length === 0 && openRowId === null) return null;

  return (
    <>
      {plans.length > 0 && (
        <Section title="Bekleyen kararlar" hint={`${plans.length} plan kararını bekliyor`} bodyClassName="px-3.5 py-1">
          <RowList as="ul">
            {plans.map((plan) => (
              <li key={plan.plan_row_id}>
                <button
                  type="button"
                  onClick={() => setOpenRowId(plan.plan_row_id)}
                  className="flex w-full items-start gap-2.5 py-2 text-left"
                >
                  <ListChecks size={13} className="mt-1 shrink-0 text-icon" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-body font-medium text-primary hover:text-accent">
                      {plan.title}
                    </span>
                    <span className="mt-0.5 block text-meta text-muted">
                      {`${plan.step_count} adım · ${plan.mutation_count} mutasyon`}
                    </span>
                    <span className="block text-meta text-muted">{expiryText(plan.expires_at)}</span>
                  </span>
                  <Chip tone={STATE_TONE[plan.state] ?? "neutral"} title={plan.revision}>
                    {PLAN_STATE_LABELS[plan.state] ?? plan.state}
                  </Chip>
                </button>
              </li>
            ))}
          </RowList>
        </Section>
      )}
      {openRowId !== null && <PlanReviewModal planRowId={openRowId} onClose={() => setOpenRowId(null)} />}
    </>
  );
}

function PlanReviewModal({ planRowId, onClose }: { planRowId: number; onClose: () => void }) {
  const [revisionHint, setRevisionHint] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const { data: plan } = useQuery({
    queryKey: ["execution-plan", planRowId],
    queryFn: () => fetchExecutionPlan(planRowId),
  });

  const decide = useMutation({
    mutationKey: ["execution-decision"],
    mutationFn: (decision: Decision) => {
      switch (decision.kind) {
        case "approve":
          return approveExecutionPlan(planRowId, decision.revision);
        case "reject":
          return rejectExecutionPlan(planRowId);
        case "cancel":
          return cancelExecutionPlan(planRowId);
        case "respond":
          return respondExecutionPlan(planRowId, decision.answers);
        case "execute":
          return runExecutionPlan(planRowId, decision.revision);
      }
    },
    onSuccess: (_view, decision) => {
      invalidateAfter("execution.write");
      if (decision.kind === "execute") {
        const surfaces = decision.actions.map((action) => ACTION_SURFACE[action]).filter(Boolean);
        if (surfaces.length > 0) invalidateAfter(...surfaces);
      }
    },
  });

  // GET detay sunucuda TTL'i uygular; yine de uzun acik kalan bir modalde
  // saat gecmisse yurutulemeyecek bir karar SUNULMAZ.
  const expired = plan?.expires_at ? expiryElapsed(plan.expires_at) : false;
  // Cevaplar soru METNI ile anahtarlanir (sunucu anahtari 64 karaktere kirpar):
  // Hermes `input_answers`'i okurken soruyu cevapla eslestirebilsin.
  const answered = (plan?.input_questions ?? []).every((question) => (answers[question] ?? "").trim().length > 0);

  // Karar butonlari SUNUCUNUN durum makinesinden turetilir: terminal planda
  // hicbiri cizilmez, footer da bos bir serit olarak kalmaz.
  const canApprove = plan ? canTransition(plan.state, "approved") : false;
  const canExecute = plan ? canTransition(plan.state, "executing") : false;
  const canRespond = plan ? canTransition(plan.state, "draft") : false;
  const canReject = plan ? canTransition(plan.state, "rejected") : false;
  const canCancel = plan ? canTransition(plan.state, "cancelled") : false;
  const canDecide = canApprove || canExecute || canRespond || canReject || canCancel;

  return (
    <Modal
      open
      onClose={onClose}
      title={plan?.title ?? "Plan inceleniyor"}
      hint={plan ? `${plan.step_count} adım · ${plan.mutation_count} mutasyon` : undefined}
      className="sm:max-w-lg"
      footer={
        canDecide &&
        plan && (
          <div className="flex flex-wrap items-center gap-2">
            {canApprove && (
              <Button
                variant="primary"
                disabled={decide.isPending || expired}
                onClick={() => decide.mutate({ kind: "approve", revision: plan.revision })}
              >
                Onayla
              </Button>
            )}
            {canExecute && (
              <Button
                variant="primary"
                disabled={decide.isPending || expired}
                onClick={() =>
                  decide.mutate({
                    kind: "execute",
                    revision: plan.revision,
                    actions: plan.steps.map((step) => step.action),
                  })
                }
              >
                {decide.isPending ? "Yürütülüyor…" : "Yürüt"}
              </Button>
            )}
            {canRespond && (
              <Button
                variant="primary"
                disabled={decide.isPending || !answered}
                onClick={() => decide.mutate({ kind: "respond", answers })}
              >
                Yanıtla
              </Button>
            )}
            {canApprove && (
              <Button onClick={() => setRevisionHint((current) => !current)} ariaExpanded={revisionHint}>
                Düzenle
              </Button>
            )}
            {canReject && (
              <Button disabled={decide.isPending} onClick={() => decide.mutate({ kind: "reject" })}>
                Reddet
              </Button>
            )}
            {canCancel && (
              <Button variant="danger" disabled={decide.isPending} onClick={() => decide.mutate({ kind: "cancel" })}>
                İptal
              </Button>
            )}
          </div>
        )
      }
    >
      {plan === undefined ? (
        <SkeletonRows rows={4} />
      ) : (
        <div className="space-y-3.5">
          {plan.summary && <p className="text-body text-secondary">{plan.summary}</p>}

          <Meta label="Neden">{plan.reason ?? "Gerekçe belirtilmemiş."}</Meta>
          <Meta label="Kanıt">
            {plan.source_refs.length + plan.evidence_refs.length === 0 ? (
              <span className="text-muted">Kanıt referansı yok.</span>
            ) : (
              <span className="flex flex-wrap gap-1">
                {/* Doğrulanmış ile yalnızca çözümlenemeyen referans AYNI
                    görünmemeli: "kanıt" etiketi fazla şey vaat etmesin. */}
                {[...plan.source_refs, ...plan.evidence_refs].map((ref) => (
                  <Chip key={ref} size="xs" title={ref}>
                    {shortRef(ref)}
                    {/* Çözümlenemeyen referans "doğrulanmış kanıt" gibi
                        görünmemeli: işaret görünür metinde taşınır. */}
                    {(plan.unresolved_refs ?? []).includes(ref) ? " (çözülemedi)" : ""}
                  </Chip>
                ))}
              </span>
            )}
          </Meta>
          <Meta label="Son geçerlilik">
            {plan.expires_at === null
              ? "Süresiz (karar beklenmiyor)."
              : `${localTime(plan.expires_at)} · ${expiryText(plan.expires_at)}`}
          </Meta>
          <Meta label="Revizyon">
            <span className="numeral" title={plan.revision}>
              {shortRevision(plan.revision)}
            </span>
            {!plan.is_current_revision && <span className="ml-2 text-warn">daha yeni bir revizyon var</span>}
          </Meta>
          <Meta label="Durum">
            <Chip tone={STATE_TONE[plan.state] ?? "neutral"}>{PLAN_STATE_LABELS[plan.state] ?? plan.state}</Chip>
            {plan.approved_revision && (
              <span className="ml-2 numeral text-meta text-muted" title={plan.approved_revision}>
                {`onaylı: ${shortRevision(plan.approved_revision)}`}
              </span>
            )}
          </Meta>

          {expired && (
            <Note tone="warn" icon={<AlertTriangle size={13} />}>
              Planın karar süresi doldu: bu revizyon artık yürütülemez. Aynı iş için Hermes'ten yeni bir revizyon
              isteyin.
            </Note>
          )}
          {revisionHint && (
            <Note tone="neutral" icon={<PencilLine size={13} />}>
              Plan içeriği doğrudan düzenlenemez: onaylanan şey tam olarak bu revizyondur. Değişiklik için Hermes'e yeni
              revizyon hazırlat (Hermes kanalında "bu planı şu değişiklikle yeniden hazırla"). Yeni revizyon yeniden
              onay ister; eski onay yeni içeriğe geçmez.
            </Note>
          )}
          {plan.state === "input_required" && plan.input_questions.length > 0 && (
            <Note tone="warn" icon={<AlertTriangle size={13} />}>
              <span className="block">
                Plan onaya hazır değil: eksik bilgi tamamlanmadan onaylanamaz. Cevaplar mutasyon üretmez; plan yeni bir
                revizyon olarak yeniden hazırlanır.
              </span>
              <span className="mt-2 block space-y-2">
                {plan.input_questions.map((question) => (
                  <Field key={question} label={question}>
                    <Input
                      value={answers[question] ?? ""}
                      onChange={(value) => setAnswers((current) => ({ ...current, [question]: value }))}
                    />
                  </Field>
                ))}
              </span>
            </Note>
          )}

          <div>
            <p className="label-caps mb-1 text-muted">Adımlar</p>
            <RowList as="ol">
              {plan.steps.map((step, index) => (
                <li key={step.step_id} className="flex items-start gap-2.5 py-2">
                  <span className="numeral mt-0.5 w-4 shrink-0 text-meta text-muted">{index + 1}</span>
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-1.5">
                      <Chip size="xs" tone="accent">
                        {step.action}
                      </Chip>
                      {stepTarget(step) && <span className="text-meta text-muted">{`hedef ${stepTarget(step)}`}</span>}
                    </span>
                    {step.description && (
                      <span className="mt-1 block text-body text-secondary">{step.description}</span>
                    )}
                  </span>
                </li>
              ))}
            </RowList>
          </div>

          {plan.receipts.length > 0 && (
            <div>
              <p className="label-caps mb-1 flex items-center gap-1.5 text-muted">
                <ShieldCheck size={12} /> Yürütme sonucu
              </p>
              <p className="mb-1 text-body text-secondary">
                {`Nihai durum: ${finalLabel(plan)}`}
                {plan.failure_code && <span className="ml-2 numeral text-danger">{plan.failure_code}</span>}
              </p>
              <RowList as="ul">
                {plan.receipts.map((receipt) => (
                  <li key={receipt.step_id} className="flex items-start gap-2.5 py-2">
                    <span className="numeral mt-0.5 w-4 shrink-0 text-meta text-muted">{receipt.ordinal + 1}</span>
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-1.5">
                        <span className="text-body text-primary">{receipt.action}</span>
                        <Chip size="xs" tone={RECEIPT_TONE[receipt.status] ?? "neutral"}>
                          {receipt.status}
                        </Chip>
                        {receipt.error_code && (
                          <span className="numeral text-meta text-danger">{receipt.error_code}</span>
                        )}
                      </span>
                      {receipt.result_ref && (
                        <span className="mt-0.5 block truncate text-meta text-muted" title={receipt.result_ref}>
                          {`sonuç: ${shortRef(receipt.result_ref)}`}
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </RowList>
              <p className="mt-1 text-meta text-muted">
                İlk hatada durulur; otomatik geri alma yoktur. Makbuzu olmayan yarım adım "mutabakat gerekli" sayılır ve
                körlemesine tekrarlanmaz.
              </p>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

/** Etiket + deger satiri (form degil: salt okunur plan karti). */
function Meta({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="label-caps w-24 shrink-0 pt-0.5 text-muted">{label}</span>
      <span className="min-w-0 flex-1 text-body text-secondary">{children}</span>
    </div>
  );
}

function Note({ tone, icon, children }: { tone: "neutral" | "warn"; icon: ReactNode; children: ReactNode }) {
  return (
    <div
      className={
        tone === "warn"
          ? "rounded-card border border-warn-border bg-warn-surface px-3 py-2 text-meta text-warn"
          : "rounded-card border border-subtle bg-surface-sunken px-3 py-2 text-meta text-secondary"
      }
    >
      <div className="flex items-start gap-1.5">
        <span className="mt-0.5 shrink-0">{icon}</span>
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </div>
  );
}

/** Adimin hedefi: H1 hedef alani (`write_registry.target_field`) `*_id`dir. */
function stepTarget(step: ExecutionStepView): string | null {
  const key = Object.keys(step.arguments).find((name) => name.endsWith("_id"));
  const value = key ? step.arguments[key] : undefined;
  return value ? shortRef(String(value)) : null;
}

/** Nihai durum etiketi (final_status yoksa plan durumu). */
function finalLabel(plan: ExecutionPlanView): string {
  const state = (plan.final_status ?? plan.state) as ExecutionPlanState;
  return PLAN_STATE_LABELS[state] ?? plan.state;
}

/** `plan-v1:<sha256>` rozet/satirda okunur kalsin. */
function shortRevision(revision: string): string {
  return revision.length > 18 ? `${revision.slice(0, 18)}…` : revision;
}

/** Kanit ve sonuc referanslari: kimligin basi; tamami `title`'da durur. */
function shortRef(ref: string): string {
  const value = ref.includes(":") ? (ref.split(":").pop() ?? ref) : ref;
  return value.length > 12 ? `${value.slice(0, 12)}…` : value;
}

/** `expires_at` gecmis mi? (Butonlari kapatir; sunucu da reddeder.) */
function expiryElapsed(iso: string): boolean {
  return new Date(iso).getTime() <= Date.now();
}

/**
 * "Son gecerlilik" metni. `expires_at` GELECEKTE oldugu icin `relativeTime`
 * ("3 gün önce") yaniltirdi: gecmis damgada o kullanilir, gelecekte kalan
 * sure yazilir.
 */
function expiryText(iso: string | null): string {
  if (!iso) return "süresiz";
  const remaining = new Date(iso).getTime() - Date.now();
  if (remaining <= 0) return `süresi doldu (${relativeTime(iso)})`;
  const minutes = Math.round(remaining / 60_000);
  if (minutes < 60) return `${Math.max(1, minutes)} dk içinde doluyor`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} sa içinde doluyor`;
  return `${Math.round(hours / 24)} gün içinde doluyor`;
}

/** Mutlak yerel zaman: "3 gün içinde doluyor" ifadesinin yaninda kesin an. */
function localTime(iso: string): string {
  return new Date(iso).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" });
}
