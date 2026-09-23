/**
 * Agent & Bilgi — ajan sınırlarının kontrol merkezi.
 *
 * Bu yüzey dört soruyu yanıtlar: forkOS sağlıklı mı, f0rknbrain bağlı mı,
 * agent bağlantısı hazır mı, ajan davranışını hangi güvenli sınırlar kontrol
 * ediyor? Tanılamadır + yapılandırmadır; KARAR YÜZEYİ DEĞİLDİR: bekleyen
 * kararları onaylamak/yürütmek için tek yer Home → Bekleyen kararlar'dır.
 *
 * Dürüstlük kuralı: forkOS kendi MCP sunucusunun hazır olduğunu bilir; Hermes
 * istemcisinin bağlı olduğunu, modelini veya trust ayarını BİLEMEZ. Bu yüzeyde
 * "Hermes bağlı" gibi bir durum gösterilmez; yalnız bağlantı tarifi ve sahiplik
 * sınırı anlatılır.
 *
 * Her kart kendi sorgusunu taşır: bir tanılamanın düşmesi sayfanın geri
 * kalanını düşürmez (§40). Paylaşılan sorgu anahtarları sayesinde aynı uca
 * birden fazla istek gitmez.
 */
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpen, CalendarDays, ChevronDown, ExternalLink, Inbox, RefreshCw, ShieldCheck } from "lucide-react";
import { navigate } from "@/app/router";
import { AGENT_LIFECYCLE_STATUS_KEY, getAgentLifecycleStatus } from "@/core/agentLifecycle";
import { AGENT_CONTINUITY_STATUS_KEY, getAgentContinuityStatus } from "@/core/agentContinuity";
import { AGENT_EPISODE_STATUS_KEY, getAgentEpisodeStatus } from "@/core/agentEpisode";
import {
  AGENT_SEMANTIC_STATUS_KEY,
  AGENT_SEMANTIC_CANDIDATES_KEY,
  getAgentSemanticStatus,
  listSemanticCandidates,
  refreshSemanticCandidates,
  confirmSemanticCandidate,
  rejectSemanticCandidate,
  promoteSemanticCandidate,
} from "@/core/agentSemantic";
import { invalidateAfter } from "@/core/invalidation";
import {
  AGENT_STATUS_KEY,
  brainReadiness,
  getAgentStatus,
  type BrainFamilyView,
  type BrainReadiness,
  type BrainStatusView,
  type LocalCognitionSlotView,
  type LocalCognitionState,
  type LocalCognitionView,
} from "@/core/agentStatus";
import {
  recentExecutionPlans,
  summarizeExecutionPlans,
  type ExecutionPlanView,
  type ExecutionResultState,
  type ExecutionSummary,
} from "@/core/execution";
import {
  describeVaultState,
  getVaultStatus,
  openObsidianUri,
  refreshVaultIndex,
  VAULT_STATUS_KEY,
  type VaultState,
} from "@/core/obsidian";
import { PROACTIVITY_STATUS_KEY, proactivityStatus } from "@/core/proactivity";
import { useSystemStats } from "@/core/runtimeQueries";
import { Button, Chip, CopyButton, Disclosure, Section, Skeleton, cx, relativeTime, useToast } from "@/core/ui";
import { formatTrDateTime } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { ProactivitySection } from "./ProactivitySection";

/* ── Ortak küçük parçalar ─────────────────────────────────────────────────
   Durum bilgisi RENGE TEK BAŞINA bağlı değildir: her satır anlamı metinle
   söyler, renk yalnız pekiştirir. */

type Tone = "neutral" | "ok" | "warn" | "danger" | "accent";

const TONE_TEXT: Record<Tone, string> = {
  neutral: "text-primary",
  ok: "text-ok",
  warn: "text-warn",
  danger: "text-danger",
  accent: "text-accent",
};

/** Etiket + değer satırı: tanılama kartlarının tek okuma ritmi. */
function StatusRow({
  label,
  value,
  tone = "neutral",
  hint,
}: {
  label: string;
  value: string;
  tone?: Tone;
  hint?: string;
}) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 py-0.5">
      <span className="w-28 shrink-0 text-meta text-secondary">{label}</span>
      <span className={cx("text-meta font-medium", TONE_TEXT[tone])}>{value}</span>
      {hint && <span className="text-micro text-muted">{hint}</span>}
    </div>
  );
}

/** Kart gövdesi: yükleniyor / hata / içerik. Hata yalnız o kartı etkiler. */
function CardBody({
  isLoading,
  isError,
  errorLabel,
  onRetry,
  children,
}: {
  isLoading: boolean;
  isError: boolean;
  errorLabel: string;
  onRetry: () => void;
  children: React.ReactNode;
}) {
  if (isError) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-meta text-warn">{errorLabel} alınamadı.</p>
        <Button variant="ghost" size="sm" onClick={onRetry}>
          <RefreshCw size={13} /> Yeniden dene
        </Button>
      </div>
    );
  }
  if (isLoading) return <Skeleton className="h-16" />;
  return <>{children}</>;
}

/* ── Sorgular (paylaşılan anahtarlar: aynı uca iki kez gidilmez) ───────── */

function useAgentStatusQuery() {
  return useQuery({ queryKey: [AGENT_STATUS_KEY], queryFn: getAgentStatus });
}

function useVaultQuery() {
  return useQuery({ queryKey: [VAULT_STATUS_KEY], queryFn: getVaultStatus });
}

function useProactivityStatusQuery() {
  return useQuery({ queryKey: [PROACTIVITY_STATUS_KEY], queryFn: proactivityStatus });
}

function useRecentExecutions() {
  return useQuery({ queryKey: ["execution-plans", "recent"], queryFn: () => recentExecutionPlans(20) });
}

/* ── Okunabilir durum sözlükleri ──────────────────────────────────────── */

const BRAIN_READINESS: Record<BrainReadiness, { label: string; tone: Tone }> = {
  ready: { label: "hazır", tone: "ok" },
  degraded: { label: "yerel sınırda değil", tone: "warn" },
  unavailable: { label: "ulaşılamıyor", tone: "danger" },
};

const LOCAL_MODEL_STATE: Record<LocalCognitionState, { label: string; tone: Tone; hint: string }> = {
  disabled: {
    label: "kapalı",
    tone: "neutral",
    hint: "İsteğe bağlı katman: yerel model olmadan forkOS normal çalışır.",
  },
  not_configured: { label: "yapılandırılmadı", tone: "warn", hint: "Model kimlikleri ayarlanmamış." },
  provider_unreachable: {
    label: "sağlayıcı erişilemiyor",
    tone: "warn",
    hint: "Yerel model sunucusu yanıt vermiyor.",
  },
  model_missing: { label: "model eksik", tone: "warn", hint: "Yapılandırılan model kurulu değil." },
  ready: { label: "hazır", tone: "ok", hint: "" },
};

/** Son yürütme sonucu: `partial` KISMİ sonuçtur, başarı gibi gösterilmez. */
const RESULT_STATE: Record<ExecutionResultState, { label: string; tone: Tone }> = {
  completed: { label: "tamamlandı", tone: "ok" },
  partial: { label: "kısmi", tone: "warn" },
  failed: { label: "başarısız", tone: "danger" },
};

const VAULT_TONE: Record<VaultState["kind"], Tone> = {
  ready: "ok",
  read_only: "warn",
  not_configured: "neutral",
  unavailable: "warn",
  unreadable: "danger",
};

/** Vault durumunun tek cümlelik karşılığı. */
const VAULT_HEADLINE: Record<VaultState["kind"], string> = {
  ready: "Bağlı ve hazır",
  read_only: "Erişilebilir ancak salt okunur",
  not_configured: "Vault runtime'a bağlanmamış",
  unavailable: "Yapılandırılmış ancak erişilemiyor",
  unreadable: "Durum okunamadı",
};

/* ── Sahiplik notu: üç sistem, üç sorumluluk ──────────────────────────── */

function OwnershipNote() {
  const rows = [
    { name: "Hermes", role: "akıl yürütür ve orkestre eder" },
    { name: "forkOS", role: "canlı operasyonel durumu tutar" },
    { name: "f0rknbrain", role: "kalıcı bilgiyi tutar" },
  ];
  return (
    <div className="rounded-card border border-subtle bg-surface px-3.5 py-2.5">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        {rows.map((row) => (
          <span key={row.name} className="text-meta text-secondary">
            <span className="font-medium text-primary">{row.name}</span> → {row.role}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ── Genel durum: skor değil, betimleyici özet ────────────────────────── */

function ReadinessSummary() {
  const system = useSystemStats();
  const agent = useAgentStatusQuery();
  const vault = useVaultQuery();
  const proactivity = useProactivityStatusQuery();
  const executions = useRecentExecutions();
  const semantic = useQuery({ queryKey: [AGENT_SEMANTIC_STATUS_KEY], queryFn: getAgentSemanticStatus });

  const vaultState = describeVaultState(vault.data, vault.isError);
  const brain = BRAIN_READINESS[brainReadiness(agent.data?.brain, agent.isError)];
  const h4 = LOCAL_MODEL_STATE[agent.data?.local_cognition.state ?? "disabled"];
  const summary: ExecutionSummary = summarizeExecutionPlans(executions.data ?? []);

  const forkos = system.isError
    ? { label: "ulaşılamıyor", tone: "danger" as Tone }
    : { label: "hazır", tone: "ok" as Tone };
  const proactivityState = proactivity.isError
    ? { label: "durum okunamadı", tone: "warn" as Tone }
    : proactivity.data?.enabled
      ? { label: "açık", tone: "ok" as Tone }
      : { label: "kapalı", tone: "neutral" as Tone };
  const h7 = executions.isError
    ? { label: "durum okunamadı", tone: "warn" as Tone }
    : summary.pending > 0
      ? { label: `${summary.pending} bekleyen karar`, tone: "warn" as Tone }
      : { label: "bekleyen karar yok", tone: "ok" as Tone };
  const needsReview = semantic.data?.needs_review_count ?? 0;
  const durableCards = semantic.data?.durable_card_count ?? 0;
  const semanticState = semantic.isError
    ? { label: "durum okunamadı", tone: "warn" as Tone }
    : needsReview > 0
      ? { label: `${needsReview} inceleme bekliyor`, tone: "warn" as Tone }
      : { label: `${durableCards} kalıcı kart`, tone: "ok" as Tone };

  return (
    <Section title="Genel durum" hint="skor değil; her bileşen kendi durumunu söyler">
      <div className="divide-y divide-subtle">
        <StatusRow label="forkOS" value={forkos.label} tone={forkos.tone} />
        <StatusRow
          label="Agent bağlantısı"
          value={brain.label}
          tone={brain.tone}
          hint={agent.data ? `${agent.data.brain.tool_count} araç` : undefined}
        />
        <StatusRow label="f0rknbrain" value={VAULT_HEADLINE[vaultState.kind]} tone={VAULT_TONE[vaultState.kind]} />
        <StatusRow label="Yerel model" value={h4.label} tone={h4.tone} />
        <StatusRow label="Hafıza adayları" value={semanticState.label} tone={semanticState.tone} />
        <StatusRow label="Proaktivite" value={proactivityState.label} tone={proactivityState.tone} />
        <StatusRow label="Bekleyen kararlar" value={h7.label} tone={h7.tone} />
      </div>
    </Section>
  );
}

/* ── Agent bağlantısı ────────────────────────────────────────────────── */

const TRANSPORT_LABEL: Record<string, string> = { streamable_http: "Streamable HTTP" };

function AgentConnectionCard() {
  const query = useAgentStatusQuery();
  const lifecycle = useQuery({ queryKey: [AGENT_LIFECYCLE_STATUS_KEY], queryFn: getAgentLifecycleStatus });
  const continuity = useQuery({ queryKey: [AGENT_CONTINUITY_STATUS_KEY], queryFn: getAgentContinuityStatus });
  const brain: BrainStatusView | undefined = query.data?.brain;
  const readiness = BRAIN_READINESS[brainReadiness(brain, query.isError)];

  return (
    <Section title="Agent bağlantısı" action={<Chip tone={readiness.tone}>{readiness.label}</Chip>}>
      <CardBody
        isLoading={query.isLoading}
        isError={query.isError}
        errorLabel="Agent bağlantısı durumu"
        onRetry={() => void query.refetch()}
      >
        {brain && (
          <div className="space-y-2">
            <div className="divide-y divide-subtle">
              <StatusRow label="Sunucu" value={brain.server_name} />
              <StatusRow label="Taşıma" value={TRANSPORT_LABEL[brain.transport] ?? brain.transport} />
              <StatusRow label="Araç yüzeyi" value={`${brain.tool_count} sınırlı araç`} />
              <StatusRow
                label="Yerel sınır"
                value={brain.loopback_only ? "yalnız 127.0.0.1" : "yerel sınır dışında"}
                tone={brain.loopback_only ? "neutral" : "warn"}
              />
            </div>

            <div className="border-t border-subtle pt-2">
              <p className="text-micro text-muted">Oturum devamlılığı</p>
              <p className="text-meta text-primary">
                {lifecycle.isLoading
                  ? "Durum yükleniyor…"
                  : lifecycle.isError
                    ? "Oturum olayları alınamadı"
                    : lifecycle.data?.last_event_at
                      ? `Son agent oturumu olayı ${relativeTime(lifecycle.data.last_event_at)}`
                      : "Henüz oturum olayı görülmedi"}
              </p>
              <div className="mt-2 divide-y divide-subtle">
                <StatusRow
                  label="Başlangıç bağlamı"
                  value={
                    continuity.isLoading
                      ? "Durum yükleniyor…"
                      : continuity.isError
                        ? "Kullanılamıyor"
                        : continuity.data?.is_truncated
                          ? "Kısmi (kırpıldı)"
                          : "Hazır (4.0 KB)"
                  }
                  tone={continuity.data?.is_truncated ? "warn" : "ok"}
                />
                <StatusRow
                  label="Son bağlam"
                  value={
                    continuity.isLoading
                      ? "Durum yükleniyor…"
                      : continuity.data?.last_context_at
                        ? relativeTime(continuity.data.last_context_at)
                        : continuity.data?.last_bootstrap_at
                          ? relativeTime(continuity.data.last_bootstrap_at)
                          : "Henüz oluşturulmadı"
                  }
                />
                <StatusRow
                  label="Kaynak devamlılığı"
                  value={
                    continuity.isLoading
                      ? "Durum yükleniyor…"
                      : continuity.data?.active_source_count
                        ? `${continuity.data.active_source_count} kaynak etkin`
                        : "Etkin kaynak yok"
                  }
                  tone={continuity.data?.active_source_count ? "ok" : "neutral"}
                />
              </div>
              <p className="mt-1.5 text-micro text-muted">Bu kayıt, Hermes’in şu anda bağlı olduğunu göstermez.</p>
            </div>

            <div className="rounded-control border border-subtle bg-surface-sunken px-2.5 py-2">
              <p className="text-micro text-muted">MCP adresi</p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <code className="min-w-0 flex-1 break-all font-mono text-meta text-primary">{brain.endpoint}</code>
                <CopyButton text={brain.endpoint} ariaLabel="MCP adresini kopyala" />
              </div>
            </div>

            <Disclosure summary={`Yetenek aileleri (${brain.families.length})`}>
              <div className="space-y-1">
                {brain.families.map((family: BrainFamilyView) => (
                  <div key={family.id} className="flex items-baseline gap-2">
                    <span className="text-meta text-primary">{family.label}</span>
                    <span className="ml-auto shrink-0 text-meta text-secondary">{family.tool_count}</span>
                  </div>
                ))}
              </div>
            </Disclosure>

            <p className="border-t border-subtle pt-2 text-micro text-muted">
              Hermes bu uca MCP üzerinden bağlanır. forkOS, Hermes istemcisinin bağlı olup olmadığını doğrulayamaz.
            </p>
          </div>
        )}
      </CardBody>
    </Section>
  );
}

/* ── f0rknbrain ──────────────────────────────────────────────────────── */

function VaultCard({ online }: { online: boolean }) {
  const toast = useToast();
  const query = useVaultQuery();
  const status = query.data;
  const state = describeVaultState(status, query.isError);
  const conflicts = Object.entries(status?.conflict_details ?? {});
  const invalidFiles = status?.invalid_files ?? [];

  const refresh = useMutation({
    mutationFn: refreshVaultIndex,
    onSuccess: () => {
      void query.refetch();
      toast.push("Vault indeksi yenilendi.", { tone: "ok" });
    },
    onError: (error: Error) => toast.push(`İndeks yenilenemedi: ${error.message}`, { tone: "danger" }),
  });

  const actions = [
    { id: "vault", label: "Vault'u Aç", icon: ExternalLink, uri: status?.open_uri },
    { id: "inbox", label: "Inbox'u Aç", icon: Inbox, uri: status?.inbox_uri },
    { id: "daily", label: "Bugünün Notunu Aç", icon: CalendarDays, uri: status?.daily_uri },
  ].filter((action) => action.uri);

  return (
    <Section
      title="f0rknbrain"
      hint={status?.vault_name}
      action={<Chip tone={VAULT_TONE[state.kind]}>{state.chip}</Chip>}
    >
      <CardBody
        isLoading={query.isLoading}
        isError={query.isError}
        errorLabel="Vault durumu"
        onRetry={() => void query.refetch()}
      >
        <div className="space-y-2.5">
          <div>
            <p className={cx("text-body font-medium", TONE_TEXT[VAULT_TONE[state.kind]])}>
              {VAULT_HEADLINE[state.kind]}
            </p>
            {state.kind === "not_configured" && (
              <p className="mt-0.5 text-meta text-muted">
                forkOS normal çalışır ancak kalıcı bilgi erişimi kullanılamaz: Vault runtime&apos;a bağlanmadan bilgi
                köprüsü kapalı kalır.
              </p>
            )}
            {state.kind === "read_only" && (
              <p className="mt-0.5 text-meta text-muted">Bilgi okuma çalışır; capture ve günlük not yazma çalışmaz.</p>
            )}
            {state.hint && state.kind !== "read_only" && state.kind !== "not_configured" && (
              <p className="mt-0.5 text-meta text-muted">{state.hint}</p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-meta text-secondary">
            <span>{status?.managed_files ?? 0} yönetilen not</span>
            <span aria-hidden>·</span>
            <span>{status?.readable ? "okunabilir" : "okunamıyor"}</span>
            <span aria-hidden>·</span>
            <span>{status?.writable ? "yazılabilir" : "salt okunur"}</span>
            <span aria-hidden>·</span>
            <span className={conflicts.length > 0 ? "text-danger" : undefined}>{conflicts.length} çakışma</span>
          </div>

          {status?.diagnostic && <p className="text-micro text-muted">{status.diagnostic}</p>}

          <div className="flex flex-wrap items-center gap-1.5">
            {actions.map(({ id, label, icon: Icon, uri }) => (
              <Button key={id} size="sm" onClick={() => uri && openObsidianUri(uri)}>
                <Icon size={13} /> {label}
              </Button>
            ))}
            <Button
              variant="ghost"
              size="sm"
              disabled={!online || !status?.available || refresh.isPending}
              title="Yerel Vault indeksini yeniden okur"
              ariaLabel="İndeksi Yenile"
              onClick={() => refresh.mutate()}
            >
              <RefreshCw size={13} /> {refresh.isPending ? "Yenileniyor…" : "İndeksi Yenile"}
            </Button>
          </div>

          {conflicts.length > 0 && (
            <div className="rounded-control border border-danger-border bg-danger-surface px-2.5 py-2">
              <p className="text-meta font-medium text-danger">
                Aynı forkOS kimliği birden fazla Vault dosyasında bulunuyor.
              </p>
              <p className="mt-0.5 text-micro text-danger">
                Dosyaları Obsidian&apos;da düzeltip indeksi yenile. forkOS bu dosyaları kendiliğinden silmez veya
                birleştirmez.
              </p>
              <Disclosure summary={`Çakışan kayıtlar (${conflicts.length})`}>
                <div className="space-y-2">
                  {conflicts.map(([id, paths]) => (
                    <div key={id} className="text-micro">
                      <p className="font-mono text-danger">{id}</p>
                      <ul className="mt-0.5 space-y-0.5">
                        {paths.map((path) => (
                          <li key={path} className="break-all text-secondary">
                            {path}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </Disclosure>
            </div>
          )}

          {invalidFiles.length > 0 && (
            <div className="rounded-control border border-warn-border bg-warn-surface px-2.5 py-2">
              <p className="text-meta font-medium text-warn">
                {invalidFiles.length} dosya geçerli forkOS metadata&apos;sı taşımıyor.
              </p>
              <p className="mt-0.5 text-micro text-warn">
                Bu bir kimlik çakışması değildir: dosya okunamadı ya da frontmatter&apos;ı bozuk.
              </p>
              <Disclosure summary={`Geçersiz dosyalar (${invalidFiles.length})`}>
                <ul className="space-y-0.5">
                  {invalidFiles.map((path) => (
                    <li key={path} className="break-all text-micro text-secondary">
                      {path}
                    </li>
                  ))}
                </ul>
              </Disclosure>
            </div>
          )}

          <Button variant="ghost" size="sm" onClick={() => navigate("/notes")}>
            <BookOpen size={13} /> Bilgi alanını aç
          </Button>
        </div>
      </CardBody>
    </Section>
  );
}

/* ── Yerel model ─────────────────────────────────────────────────────── */

function ModelSlotRow({ label, slot }: { label: string; slot: LocalCognitionSlotView | undefined }) {
  const configured = Boolean(slot?.configured);
  const value = !configured ? "yapılandırılmadı" : slot?.available ? "kurulu" : "kurulu değil";
  return <StatusRow label={label} value={value} tone={!configured ? "neutral" : slot?.available ? "ok" : "warn"} />;
}

function LocalModelCard() {
  const query = useAgentStatusQuery();
  const h4: LocalCognitionView | undefined = query.data?.local_cognition;
  const state = LOCAL_MODEL_STATE[h4?.state ?? "disabled"];

  return (
    <Section title="Yerel model" action={<Chip tone={state.tone}>{state.label}</Chip>}>
      <CardBody
        isLoading={query.isLoading}
        isError={query.isError}
        errorLabel="Yerel model durumu"
        onRetry={() => void query.refetch()}
      >
        <div className="space-y-2">
          <p className="text-meta text-secondary">
            forkOS&apos;un sınıflandırma, çıkarım ve sorgu yeniden yazma gibi küçük işleri için kullandığı isteğe bağlı
            yerel model.
          </p>
          <p className="text-meta text-muted">Hermes&apos;in sohbet modeli bundan bağımsızdır.</p>

          {h4 && (
            <>
              <div className="divide-y divide-subtle border-t border-subtle pt-1">
                <StatusRow label="Sağlayıcı" value={`${h4.provider} · ${h4.endpoint_class}`} />
                <StatusRow
                  label="Erişilebilirlik"
                  value={h4.reachable === null ? "yoklanmadı" : h4.reachable ? "erişilebilir" : "erişilemiyor"}
                  tone={h4.reachable === null ? "neutral" : h4.reachable ? "ok" : "warn"}
                />
                <ModelSlotRow label="Küçük model" slot={h4.small} />
                <ModelSlotRow label="Orta model" slot={h4.medium} />
              </div>
              {state.hint && <p className="text-micro text-muted">{state.hint}</p>}
              {h4.detail && <p className="text-micro text-muted">{h4.detail}</p>}
              {h4.state !== "disabled" && (
                <p className="text-micro text-muted">
                  Yerel model yapılandırması ortam/yapılandırma dosyasından gelir; buradan değiştirilmez.
                </p>
              )}
            </>
          )}
        </div>
      </CardBody>
    </Section>
  );
}

/* ── Bekleyen kararlar: salt okunur özet ─────────────────────────────── */

function DecisionsCard() {
  const query = useRecentExecutions();
  const plans: ExecutionPlanView[] = query.data ?? [];
  const summary: ExecutionSummary = summarizeExecutionPlans(plans);
  const result = summary.last_result ? RESULT_STATE[summary.last_result] : null;
  const latest = summary.last_result ? plans.find((plan) => plan.state === summary.last_result) : undefined;

  const resultValue = result ? result.label : plans.length === 0 ? "kayıt yok" : "sonuçlanmış plan yok";

  return (
    <Section title="Bekleyen kararlar" hint="salt okunur özet">
      <CardBody
        isLoading={query.isLoading}
        isError={query.isError}
        errorLabel="Karar özeti"
        onRetry={() => void query.refetch()}
      >
        <div className="space-y-2">
          <div className="divide-y divide-subtle">
            <StatusRow
              label="Bekleyen"
              value={summary.pending > 0 ? `${summary.pending} karar` : "karar yok"}
              tone={summary.pending > 0 ? "warn" : "neutral"}
            />
            <StatusRow
              label="Son yürütme"
              value={resultValue}
              tone={result?.tone ?? "neutral"}
              hint={latest ? relativeTime(latest.updated_at) : undefined}
            />
          </div>

          {summary.last_title && <p className="text-micro text-muted">Son plan: {summary.last_title}</p>}

          <p className="text-micro text-muted">
            Onaylama ve yürütme Home → Bekleyen kararlar yüzeyinden yapılır; burada yalnız durum gösterilir.
          </p>

          <Button size="sm" onClick={() => navigate("/")}>
            Bekleyen kararları gör
          </Button>
        </div>
      </CardBody>
    </Section>
  );
}

/* ── Hermes bağlantısı ───────────────────────────────────────────────── */

/**
 * Gerçek Hermes yapılandırmasının asgari güvenli örneği. Sözdizimi bu
 * ortamdaki `~/.hermes/config.yaml` ile aynıdır (url/enabled/trust/timeout/
 * connect_timeout/sampling); uç adresi sunucudan gelir.
 */
function hermesConfigSnippet(endpoint: string): string {
  return [
    "mcp_servers:",
    "  forkos-brain:",
    `    url: "${endpoint}"`,
    "    enabled: true",
    "    trust: untrusted",
    "    timeout: 120",
    "    connect_timeout: 30",
    "    supports_parallel_tool_calls: false",
    "    sampling:",
    "      enabled: false",
  ].join("\n");
}

function HermesCard() {
  const query = useAgentStatusQuery();
  const endpoint = query.data?.brain.endpoint ?? "";
  const snippet = endpoint ? hermesConfigSnippet(endpoint) : "";

  return (
    <Section
      title="Hermes bağlantısı"
      action={
        <Chip tone="neutral" icon={<ShieldCheck size={12} />}>
          yapılandırma Hermes tarafında
        </Chip>
      }
    >
      <div className="space-y-2.5">
        <p className="text-meta text-secondary">
          Hermes forkOS&apos;un dışında çalışır ve bu arayüze MCP üzerinden bağlanır.
        </p>

        <CardBody
          isLoading={query.isLoading}
          isError={query.isError}
          errorLabel="Bağlantı bilgisi"
          onRetry={() => void query.refetch()}
        >
          {endpoint && (
            <div className="space-y-2.5">
              <div className="rounded-control border border-subtle bg-surface-sunken px-2.5 py-2">
                <p className="text-micro text-muted">Hermes&apos;e verilecek MCP adresi</p>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <code className="min-w-0 flex-1 break-all font-mono text-meta text-primary">{endpoint}</code>
                  <CopyButton text={endpoint} label="MCP adresini kopyala" />
                </div>
              </div>

              <Disclosure summary="Gelişmiş ayarlar">
                <div className="rounded-control border border-subtle bg-surface-sunken px-2.5 py-2">
                  <pre className="overflow-x-auto font-mono text-micro leading-relaxed text-secondary">{snippet}</pre>
                </div>
                <CopyButton text={snippet} label="Ayarı kopyala" ariaLabel="Hermes ayar örneğini kopyala" />
                <p className="text-micro text-muted">
                  <span className="font-medium text-primary">trust: untrusted</span> bir Hermes İSTEMCİ ayarıdır: yazma
                  araçları kullanıcı onayı ister. Bu ayarın Hermes tarafında gerçekten açık olduğunu forkOS
                  doğrulayamaz; burada yalnız önerilen güvenli değer gösterilir.
                </p>
              </Disclosure>

              <Disclosure summary="Katmanlar: Hermes Skills · Agent hafızası · f0rknbrain">
                <div className="space-y-1 text-micro text-secondary">
                  <p>
                    <span className="font-medium text-primary">Hermes Skills</span> → Hermes&apos;in bir sistemi NASIL
                    kullanacağını öğrendiği prosedürler.
                  </p>
                  <p>
                    <span className="font-medium text-primary">Agent hafızası</span> → küratürlü, güncel operasyonel
                    hatırlatmalar.
                  </p>
                  <p>
                    <span className="font-medium text-primary">f0rknbrain</span> → kalıcı insan bilgisi.
                  </p>
                  <p className="text-muted">
                    Bu katmanlar birbirine senkronlanmaz; her birinin sahibi ayrıdır ve buradan yapılacak bir
                    &quot;hafıza eşitle&quot; işlemi yoktur.
                  </p>
                </div>
              </Disclosure>
            </div>
          )}
        </CardBody>

        <p className="border-t border-subtle pt-2 text-micro text-muted">
          Hermes&apos;in sağlayıcısı, modeli ve skill&apos;leri forkOS&apos;tan yönetilmez; bu bölüm yalnız bağlantı
          tarifini verir.
        </p>
      </div>
    </Section>
  );
}

/* ── Son oturum devri (A3) ───────────────────────────────────────────── */

/**
 * Sınırlı gerekçe kodlarının kullanıcı dilindeki karşılığı. Ham kod EKRANA
 * ÇIKMAZ: sözlükte olmayan bir kod tek nötr etikete düşer, böylece yeni bir
 * kod eklendiğinde yüzey sırıtmaz ve iç sözlük sızmaz.
 */
const EPISODE_DEGRADED_LABEL: Record<string, string> = {
  EPISODE_EXTRACTION_UNAVAILABLE: "çıkarım servisi kullanılamadı",
  EPISODE_EXTRACTION_TIMEOUT: "çıkarım süresi aşıldı",
  EPISODE_VALIDATION_FAILED: "çıkarım doğrulanamadı",
  EPISODE_EMPTY: "tura ait ifade bulunamadı",
  EPISODE_FINALIZE_DEGRADED: "mühürleme sınırlı tamamlandı",
  EPISODE_HANDOFF_UNAVAILABLE: "devir hazırlanamadı",
  EPISODE_SESSION_NOT_FOUND: "oturum kaydı bulunamadı",
  EPISODE_SEALED: "oturum zaten mühürlenmiş",
  SOURCE_BINDING_UNAVAILABLE: "kaynak bağı kurulamadı",
  SOURCE_STALE: "kaynak sürümü eskimiş",
  EPISODE_INPUT_TRUNCATED: "tur kırpılarak alındı",
  H5_UNAVAILABLE: "inceleme zekâsı kullanılamadı",
  LOCAL_COGNITION_UNAVAILABLE: "yerel model kullanılamadı",
  VERBATIM_LEAKAGE: "ham metin sızması engellendi",
  SCOPE_AMBIGUOUS: "çelişkili proje kapsamı",
  SECRET_LEAKAGE: "hassas bilgi sızması engellendi",
};

const EPISODE_DEGRADED_UNKNOWN = "sınıflandırılmamış sınırlama";

/**
 * Son mühürlenmiş oturumun metadata özeti. Devir İÇERİĞİ (ifade metinleri)
 * burada açılmaz: bu yüzey durum okur, hafıza göstermez. Hermes'in şu anda
 * bağlı olduğu da iddia edilmez.
 */
function EpisodeHandoffCard() {
  const query = useQuery({ queryKey: [AGENT_EPISODE_STATUS_KEY], queryFn: getAgentEpisodeStatus });
  const status = query.data;
  const degraded = status?.degraded_reasons ?? [];
  const limited = degraded.length > 0;

  return (
    <Section
      title="Son oturum devri"
      hint="metadata özeti"
      action={
        status ? <Chip tone={limited ? "warn" : "ok"}>{limited ? "devir sınırlı" : "devir hazır"}</Chip> : undefined
      }
    >
      <CardBody
        isLoading={query.isLoading}
        isError={query.isError}
        errorLabel="Son oturum devri"
        onRetry={() => void query.refetch()}
      >
        {status && (
          <div className="space-y-2">
            <div className="divide-y divide-subtle">
              <StatusRow
                label="Son mühürleme"
                value={status.last_sealed_at ? formatTrDateTime(status.last_sealed_at) : "henüz yok"}
                hint={status.last_sealed_at ? relativeTime(status.last_sealed_at) : undefined}
              />
              <StatusRow label="Devir öğeleri" value={`${status.last_episode_item_count} ifade`} />
              <StatusRow label="Kapsam" value={status.last_scope_project ?? "kapsamsız"} />
              <StatusRow
                label="Hazır devir"
                value={status.recent_handoff_available ? "var" : "yok"}
                tone={status.recent_handoff_available ? "ok" : "neutral"}
              />
              <StatusRow label="Durum" value={limited ? "sınırlı" : "hazır"} tone={limited ? "warn" : "ok"} />
            </div>

            {limited && (
              <ul className="space-y-0.5">
                {degraded.map((code) => (
                  <li key={code} className="text-micro text-warn">
                    · {EPISODE_DEGRADED_LABEL[code] ?? EPISODE_DEGRADED_UNKNOWN}
                  </li>
                ))}
              </ul>
            )}

            <p className="text-micro text-muted">
              Yalnız mühürlenmiş oturumun özeti gösterilir; devir içeriği burada açılmaz. Bu kayıt, Hermes&apos;in şu
              anda bağlı olduğunu göstermez.
            </p>
          </div>
        )}
      </CardBody>
    </Section>
  );
}

const EVIDENCE_LABELS: Record<string, string> = {
  explicit_user: "Kullanıcı açıkça söyledi",
  canonical_source: "Kayıtla doğrulandı",
  episode_derived: "Önceki oturumdan çıkarıldı",
  model_derived: "Agent çıkarımı",
};

const DESTINATION_LABELS: Record<string, string> = {
  durable_vault: "Kalıcı Kasa",
  hot_memory: "Sıcak Bellek",
  operational: "Operasyonel",
  procedural_candidate: "Prosedürel Aday",
  discard: "Göz Ardı",
};

const KIND_LABELS: Record<string, string> = {
  identity: "Kimlik",
  preference: "Tercih",
  correction: "Düzeltme",
  constraint: "Kısıt",
  goal: "Hedef",
  decision: "Karar",
  lesson: "Ders",
  project_knowledge: "Proje Bilgisi",
  reference: "Referans",
};

export function SemanticCandidatesCard({ online = true }: { online?: boolean }) {
  const toast = useToast();
  const statusQuery = useQuery({
    queryKey: [AGENT_SEMANTIC_STATUS_KEY],
    queryFn: getAgentSemanticStatus,
  });
  const candidatesQuery = useQuery({
    queryKey: [AGENT_SEMANTIC_CANDIDATES_KEY],
    queryFn: () => listSemanticCandidates(),
  });

  const refreshMutation = useMutation({
    mutationFn: refreshSemanticCandidates,
    onSuccess: (data) => {
      invalidateAfter("agent-semantic.write");
      toast.push(`Adaylar tarandı: ${data.created_count} yeni, ${data.updated_count} güncellenen aday.`, { tone: "ok" });
    },
    onError: () => {
      toast.push("Adaylar taranırken hata oluştu.", { tone: "danger" });
    },
  });

  const confirmMutation = useMutation({
    mutationFn: ({ id, revision }: { id: string; revision: string }) =>
      confirmSemanticCandidate(id, revision),
    onSuccess: () => {
      invalidateAfter("agent-semantic.write");
      toast.push("Aday onaylandı ve terfi için hazırlandı.", { tone: "ok" });
    },
    onError: () => {
      toast.push("Aday onaylanırken hata oluştu.", { tone: "danger" });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, revision }: { id: string; revision: string }) =>
      rejectSemanticCandidate(id, revision),
    onSuccess: () => {
      invalidateAfter("agent-semantic.write");
      toast.push("Aday reddedildi.", { tone: "ok" });
    },
    onError: () => {
      toast.push("Aday reddedilirken hata oluştu.", { tone: "danger" });
    },
  });

  const promoteMutation = useMutation({
    mutationFn: ({
      id,
      revision,
      targetDestination,
      supersedes,
    }: {
      id: string;
      revision: string;
      targetDestination?: string;
      supersedes?: string[];
    }) => promoteSemanticCandidate(id, revision, targetDestination, supersedes),
    onSuccess: (data) => {
      invalidateAfter("agent-semantic.write");
      toast.push(`Aday kalıcı bilgiye terfi ettirildi (${data.destination}).`, { tone: "ok" });
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail?.message || "Terfi işlemi başarısız oldu.";
      toast.push(msg, { tone: "danger" });
    },
  });

  const status = statusQuery.data;
  const candidates = candidatesQuery.data?.items ?? [];
  const pendingCandidates = candidates.filter(
    (c) => c.status === "proposed" || c.status === "needs_review" || c.status === "ready",
  );

  return (
    <Section
      title="Hafıza adayları"
      hint="epistemik inceleme ve kalıcı bilgi terfisi"
      action={
        <Button
          variant="secondary"
          size="sm"
          onClick={() => refreshMutation.mutate()}
          disabled={!online || refreshMutation.isPending}
        >
          <RefreshCw className={cx("mr-1.5 h-3.5 w-3.5", refreshMutation.isPending && "animate-spin")} />
          Adayları tara
        </Button>
      }
    >
      <CardBody
        isLoading={statusQuery.isLoading || candidatesQuery.isLoading}
        isError={statusQuery.isError || candidatesQuery.isError}
        errorLabel="Hafıza adayları"
        onRetry={() => {
          void statusQuery.refetch();
          void candidatesQuery.refetch();
        }}
      >
        <div className="space-y-3">
          {status && (
            <div className="divide-y divide-subtle">
              <StatusRow
                label="Kalıcı kartlar"
                value={`${status.durable_card_count} kart`}
                hint="30 Knowledge/Memory/"
                tone={status.durable_card_count > 0 ? "ok" : "neutral"}
              />
              <StatusRow
                label="İnceleme bekleyen"
                value={`${status.needs_review_count ?? 0} aday`}
                tone={(status.needs_review_count ?? 0) > 0 ? "warn" : "neutral"}
              />
              <StatusRow
                label="Onaylı / Hazır"
                value={`${status.ready_count ?? 0} aday`}
                tone={(status.ready_count ?? 0) > 0 ? "ok" : "neutral"}
              />
              <StatusRow
                label="Önerilen"
                value={`${status.proposed_count ?? 0} aday`}
                tone="neutral"
              />
            </div>
          )}

          {pendingCandidates.length === 0 ? (
            <p className="text-micro text-muted py-1">
              Bekleyen hafıza adayı yok. Oturumlar tamamlandıkça veya kaynaklar güncellendikçe adaylar burada listelenir.
            </p>
          ) : (
            <div className="space-y-2">
              <span className="text-micro font-medium text-secondary">
                Bekleyen Adaylar ({pendingCandidates.length})
              </span>
              <div className="space-y-2">
                {pendingCandidates.map((c) => {
                  const isExplicitUser = c.primary_evidence_class === "explicit_user";
                  const isReady = c.status === "ready";
                  const canPromote = isExplicitUser || isReady;
                  const isPendingAction =
                    confirmMutation.isPending || rejectMutation.isPending || promoteMutation.isPending;

                  return (
                    <div
                      key={c.id}
                      className="rounded-card border border-subtle bg-surface-raised p-2.5 space-y-1.5"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-meta font-medium text-primary leading-snug">
                          {c.statement}
                        </p>
                        <Chip
                          tone={
                            c.status === "ready"
                              ? "ok"
                              : c.status === "needs_review"
                                ? "warn"
                                : "neutral"
                          }
                        >
                          {c.status === "ready"
                            ? "Onaylı"
                            : c.status === "needs_review"
                              ? "İnceleme Gerekli"
                              : "Önerildi"}
                        </Chip>
                      </div>

                      <div className="flex flex-wrap items-center gap-1.5 text-micro text-secondary">
                        <Chip tone="accent">{KIND_LABELS[c.kind] ?? c.kind}</Chip>
                        <Chip tone="neutral">
                          {c.scope === "project" ? (c.scope_project ?? "Proje") : "Genel"}
                        </Chip>
                        <Chip tone="neutral">
                          Hedef: {DESTINATION_LABELS[c.suggested_destination] ?? c.suggested_destination}
                        </Chip>
                        <span className="text-muted">·</span>
                        <span>
                          {EVIDENCE_LABELS[c.primary_evidence_class] ?? c.primary_evidence_class}
                        </span>
                        <span className="text-muted">·</span>
                        <span>{(c.evidence_refs ?? []).length} kaynak</span>
                      </div>

                      {(c.possible_related_card_ids ?? []).length > 0 && (
                        <div className="rounded border border-subtle bg-surface px-2 py-1 text-micro text-warn">
                          Benzer mevcut bilgi: {(c.possible_related_card_ids ?? []).join(", ")}
                        </div>
                      )}

                      <div className="flex items-center gap-2 pt-1">
                        {!isReady && (
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={!online || isPendingAction}
                            onClick={() =>
                              confirmMutation.mutate({ id: c.id, revision: c.revision })
                            }
                          >
                            Onayla
                          </Button>
                        )}
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={!online || isPendingAction || !canPromote}
                          onClick={() =>
                            promoteMutation.mutate({
                              id: c.id,
                              revision: c.revision,
                              targetDestination: c.suggested_destination,
                              supersedes:
                                (c.possible_related_card_ids ?? []).length > 0
                                  ? c.possible_related_card_ids
                                  : undefined,
                            })
                          }
                        >
                          Terfi et
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={!online || isPendingAction}
                          onClick={() =>
                            rejectMutation.mutate({ id: c.id, revision: c.revision })
                          }
                        >
                          Reddet
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <p className="text-micro text-muted">
            Kalıcı hafıza f0rknbrain kasasındaki 30 Knowledge/Memory/ altında Markdown kartları olarak saklanır. Zayıf kanıtlı veya model çıkarımı olan adaylar kullanıcı onayı olmadan terfi edemez.
          </p>
        </div>
      </CardBody>
    </Section>
  );
}

/* ── Sayfa ───────────────────────────────────────────────────────────── */

export function BrainAgentSection() {
  const online = useOnline();
  return (
    <div className="space-y-4">
      <OwnershipNote />
      <ReadinessSummary />
      <div className="grid gap-4 lg:grid-cols-2">
        <AgentConnectionCard />
        <VaultCard online={online} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <LocalModelCard />
        <DecisionsCard />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <HermesCard />
        <EpisodeHandoffCard />
      </div>
      <SemanticCandidatesCard online={online} />
      <div className="space-y-0.5">
        <p className="text-meta text-secondary">Sessizlik başarılı bir sonuçtur.</p>
        <p className="text-micro text-muted">
          Proaktivite yalnız dikkat gerektiren durumlarda konuşur; sessiz kalmak bir hata değil, beklenen sonuçtur.
        </p>
      </div>
      <ProactivitySection online={online} />
    </div>
  );
}
