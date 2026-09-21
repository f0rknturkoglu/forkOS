/**
 * Sistem Durumu — bilgi mimarisi v2 (§28/§67/§86).
 *
 * Üç anlamsal grup vardır ve her grup KENDİ sorgu hatasını taşır: bir tanılama
 * düşse bile sayfanın geri kalanı ayakta kalır.
 *
 *   1. Genel bakış      — API/runtime, worker, kaynak özeti, zihin katmanı, yedek
 *   2. İlgi gerekenler  — yalnız gösterilecek bir şey varsa; yoksa tek sakin satır
 *   3. Ayrıntılı sağlık — kaynak/RSS/yedek/servis kartları (2 sütun)
 *
 * Dürüstlük sözleşmesi:
 *   NO DATA ≠ HEALTHY · QUERY ERROR ≠ HEALTHY · UNKNOWN ≠ HEALTHY
 *   `disabled`/`kapalı` bir hata DEĞİLDİR.
 * Hiçbir sorgu düştüğünde "her şey sağlıklı" cümlesi kurulmaz; genel durum
 * `overallState` ile türetilir ve bir alt sistem bilinmiyorsa "Durum kısmen
 * bilinmiyor" der. Skor/yüzde YOKTUR (§32).
 *
 * Sağlıklı envanter SAYILIR, listelenmez (§68): "42 kaynak sağlıklı" yeter;
 * kaynak kataloğunun tamamı kanonik `/sources` sayfasındadır (§69).
 *
 * Veri yalnız MEVCUT paylaşılan uçlardan gelir (yeni uç yok): /system/stats,
 * /sources/coverage, /sources/health, /rss/feeds, /rss/stats, /backup/status,
 * /agent/status, /obsidian/status, /proactivity/status, /execution/plans.
 * Anahtarlar kabuk, widget'lar ve Ayarlar ile AYNIDIR: aynı uca ikinci istek
 * gitmez. Sorgular tek yerde (`useHealthSummary`) okunur; gruplar yalnız düz
 * veriyi çizer.
 */
import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { api } from "@/core/api";
import {
  AGENT_STATUS_KEY,
  brainReadiness,
  getAgentStatus,
  type BrainReadiness,
  type BrainStatusView,
  type LocalCognitionView,
} from "@/core/agentStatus";
import { dataState, type DataState } from "@/core/DataState";
import { formatSystemDiagnostics, type SourceProblemDiagnostic } from "@/core/diagnostics";
import { recentExecutionPlans, summarizeExecutionPlans, type ExecutionSummary } from "@/core/execution";
import { sourceLabel } from "@/core/labels";
import { describeVaultState, getVaultStatus, VAULT_STATUS_KEY, type VaultState } from "@/core/obsidian";
import { PROACTIVITY_STATUS_KEY, proactivityStatus } from "@/core/proactivity";
import { useBackupStatus, useSourceHealth, useSystemStats } from "@/core/runtimeQueries";
import {
  errorKindTone,
  errorPreview,
  feedStateView,
  healthSummaryLabel,
  isProblem,
  overallState,
  overallView,
  problemReasons,
  type StatusTone,
  type StatusView,
} from "@/core/sourceStatus";
import type { BackupStatus, Feed, RssStats, SourceCoverageRow, SystemStats } from "@/core/types";
import { Button, Chip, CopyButton, PageFrame, Section, SectionHeader, cx, relativeTime } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { SetupChecklist } from "./SetupChecklist";
import { DETAIL_WIDGETS } from "./widgets";
import { formatBytes } from "./widgets/BackupHealthWidget";
import { workerStatusView, type ServiceStateView } from "./widgets/ServiceHealthWidget";

/* ── Sunum sözlüğü ────────────────────────────────────────────────────── */

const TONE_TEXT: Record<StatusTone, string> = {
  neutral: "text-primary",
  ok: "text-ok",
  warn: "text-warn",
  danger: "text-danger",
  accent: "text-accent",
};

const TONE_DOT: Record<StatusTone, string> = {
  neutral: "bg-icon",
  ok: "bg-ok",
  warn: "bg-warn",
  danger: "bg-danger",
  accent: "bg-accent",
};

/** Tek satırlık özet kalemi: değer metni ANLAMI taşır, renk yalnız pekiştirir. */
function SummaryRow({
  label,
  value,
  tone = "neutral",
  hint,
  href,
}: {
  label: string;
  value: string;
  tone?: StatusTone;
  hint?: string | null;
  href?: string;
}) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 border-b border-subtle py-2 last:border-b-0">
      <span className="w-40 shrink-0 text-meta text-secondary">{label}</span>
      <span className={cx("text-meta font-medium", TONE_TEXT[tone])}>{value}</span>
      {href && (
        <a href={href} className="text-meta text-accent hover:underline">
          aç →
        </a>
      )}
      {hint && <span className="w-full text-micro text-muted">{hint}</span>}
    </div>
  );
}

const BRAIN_READINESS: Record<BrainReadiness, { label: string; tone: StatusTone }> = {
  ready: { label: "MCP sunucusu hazır", tone: "ok" },
  degraded: { label: "yerel sınır dışında", tone: "warn" },
  unavailable: { label: "MCP yüzeyi kayıtlı değil", tone: "danger" },
};

const VAULT_TONE: Record<VaultState["kind"], StatusTone> = {
  ready: "ok",
  read_only: "warn",
  not_configured: "neutral",
  unavailable: "warn",
  unreadable: "neutral",
};

/** H4 özeti: beş durumun ayrıntılı etiketleri Ayarlar'dadır; burada yalnız
 *  "kapalı / hazır / ilgi istiyor" ayrımı yapılır ve gerekçe SUNUCUNUN kendi
 *  açıklamasından (`detail`) okunur — istemci yeni bir teşhis metni uydurmaz. */
function h4Summary(h4: LocalCognitionView): { label: string; tone: StatusTone; hint: string | null } {
  if (h4.state === "disabled") {
    return { label: "kapalı", tone: "neutral", hint: "İsteğe bağlı katman: H4 olmadan forkOS normal çalışır." };
  }
  if (h4.state === "ready") return { label: "hazır", tone: "ok", hint: h4.detail };
  return { label: "ilgi istiyor", tone: "warn", hint: h4.detail };
}

/* ── Biçimlendirme yardımcıları ───────────────────────────────────────── */

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  if (days > 0) return `${days} gün ${hours} saat`;
  if (hours > 0) return `${hours} saat ${minutes} dk`;
  return `${minutes} dk`;
}

function formatGib(bytes: number): string {
  const gib = bytes / 1024 ** 3;
  return `${gib >= 10 ? Math.round(gib) : gib.toFixed(1)} GB`;
}

/** Bellek/disk özeti: yüzde DEĞİL, kalan miktar (skor değil, kapasite). */
function resourceHint(stats: SystemStats): string {
  const parts: string[] = [`${formatUptime(stats.uptime_s)} açık`];
  if (stats.mem_total_kb !== null && stats.mem_available_kb !== null) {
    parts.push(`${formatGib(stats.mem_available_kb * 1024)} RAM boş / ${formatGib(stats.mem_total_kb * 1024)}`);
  }
  if (stats.disk) parts.push(`${formatGib(stats.disk.free)} disk boş / ${formatGib(stats.disk.total)}`);
  return parts.join(" · ");
}

/** Okunamayan bir bölümün tek cümlesi: "sorun yok" anlamına GELMEZ. */
function unknownHint(what: string): string {
  return `${what} alınamadı — durum bilinmiyor.`;
}

/* ── Tanılama paketi (§43–§47) ────────────────────────────────────────── */

/** Bir kaynak sorununu tanılama satırına çevirir (yalnız backend alanları). */
function toProblemDiagnostic(row: SourceCoverageRow): SourceProblemDiagnostic {
  return {
    source: row.source,
    label: sourceLabel(row.source),
    source_class: row.class,
    kind: row.kind,
    status: row.last_status,
    error_kind: row.last_error_kind,
    circuit_open: row.circuit_open,
    consecutive_failures: row.consecutive_failures,
    consecutive_empty: row.consecutive_empty,
    last_run_at: row.last_run_at,
    last_success_at: row.last_success_at,
    last_new_content_at: row.last_new_content_at,
    parser_version: row.parser_version,
    last_error: row.last_error,
  };
}

/* ── Özet sözleşmesi: sayfanın okuduğu TEK düz veri ───────────────────── */

interface HealthSummary {
  /* Sistem ve veri */
  statsState: DataState;
  resourceHint: string | null;
  worker: ServiceStateView;
  coverageState: DataState;
  sourceTotal: number;
  sourceHealthy: number;
  sourceProblems: SourceCoverageRow[];
  sourceNeverRan: number;
  runningSources: number;
  backupState: DataState;
  lastBackupAt: string | null;
  backupPendingChanges: boolean;
  /* Zihin katmanı */
  agentState: DataState;
  brain: BrainStatusView | null;
  brainReadiness: BrainReadiness;
  h4: { label: string; tone: StatusTone; hint: string | null } | null;
  vaultState: DataState;
  vault: VaultState;
  proactivityState: DataState;
  proactivityEnabled: boolean | null;
  executionsState: DataState;
  plans: ExecutionSummary;
  /* Gruplar */
  attentionItems: AttentionItem[];
  unknownSections: string[];
  overall: StatusView;
  bundle: string;
  loading: boolean;
  retryUnknown: () => void;
}

interface AttentionItem {
  key: string;
  text: string;
  tone: StatusTone;
  href?: string;
}

function attentionItems(input: {
  coverageState: DataState;
  sourceProblems: SourceCoverageRow[];
  failingFeeds: number | null;
  rssStatsState: DataState;
  feedsState: DataState;
  driveError: { message: string } | null;
  backupState: DataState;
  statsState: DataState;
  runsState: DataState;
  vaultState: DataState;
  vaultDegraded: boolean;
  vaultChip: string;
  agentState: DataState;
  h4Degraded: boolean;
  h4Hint: string | null;
  h4Label: string;
  proactivityState: DataState;
  executionsState: DataState;
  pendingDecisions: number;
  lastResult: ExecutionSummary["last_result"];
}): AttentionItem[] {
  const items: AttentionItem[] = [];

  if (input.coverageState === "error") {
    items.push({
      key: "sources-unknown",
      text: "Kaynak kapsamı alınamadı — durum bilinmiyor.",
      tone: "neutral",
      href: "#/sources",
    });
  } else {
    for (const problem of input.sourceProblems.slice(0, 5)) {
      items.push({
        key: `source-${problem.source}`,
        text: `${sourceLabel(problem.source)}: ${problemReasons(problem).join(" · ")}`,
        tone: problem.circuit_open || errorKindTone(problem.last_error_kind) === "danger" ? "danger" : "warn",
        href: "#/sources",
      });
    }
    if (input.sourceProblems.length > 5) {
      items.push({
        key: "sources-more",
        text: `+${input.sourceProblems.length - 5} kaynak daha ilgi istiyor`,
        tone: "warn",
        href: "#/sources",
      });
    }
  }

  if (input.failingFeeds !== null && input.failingFeeds > 0) {
    items.push({
      key: "feeds",
      text: `${input.failingFeeds} besleme ilgi istiyor (hata birikmiş ya da kapatılmış).`,
      tone: "danger",
      href: "#/rss",
    });
  }
  if (input.feedsState === "error") {
    items.push({
      key: "feeds-unknown",
      text: "RSS beslemeleri alınamadı — durum bilinmiyor.",
      tone: "neutral",
      href: "#/rss",
    });
  }
  if (input.rssStatsState === "error") {
    items.push({
      key: "rss-stats-unknown",
      text: "RSS istatistikleri alınamadı — durum bilinmiyor.",
      tone: "neutral",
      href: "#/rss",
    });
  }

  if (input.driveError) {
    items.push({
      key: "drive-error",
      text: `Drive yüklemesi başarısız oldu: ${errorPreview(input.driveError.message) ?? "bilinmeyen hata"}`,
      tone: "danger",
    });
  }
  if (input.backupState === "error") {
    items.push({ key: "backup-unknown", text: "Yedek durumu alınamadı — durum bilinmiyor.", tone: "neutral" });
  }

  if (input.vaultState === "error") {
    items.push({
      key: "vault-unknown",
      text: "Bilgi kasası durumu alınamadı — durum bilinmiyor.",
      tone: "neutral",
      href: "#/notes",
    });
  } else if (input.vaultDegraded) {
    items.push({ key: "vault", text: `Bilgi kasası: ${input.vaultChip}`, tone: "warn", href: "#/notes" });
  }

  if (input.agentState === "error") {
    items.push({
      key: "agent-unknown",
      text: "Brain Interface durumu alınamadı — durum bilinmiyor.",
      tone: "neutral",
      href: "#/settings?tab=brain",
    });
  } else if (input.h4Degraded) {
    items.push({
      key: "h4",
      text: `H4 yerel biliş: ${input.h4Hint ?? input.h4Label}`,
      tone: "warn",
      href: "#/settings?tab=brain",
    });
  }

  if (input.proactivityState === "error") {
    items.push({
      key: "proactivity-unknown",
      text: "Proaktivite durumu alınamadı — durum bilinmiyor.",
      tone: "neutral",
      href: "#/settings?tab=notifications",
    });
  }

  if (input.executionsState === "error") {
    items.push({
      key: "h7-unknown",
      text: "H7 karar özeti alınamadı — durum bilinmiyor.",
      tone: "neutral",
      href: "#/",
    });
  } else if (input.pendingDecisions > 0) {
    items.push({
      key: "h7-pending",
      text: `${input.pendingDecisions} karar onay bekliyor — Home → Bekleyen kararlar`,
      tone: "warn",
      href: "#/",
    });
  } else if (input.lastResult === "partial" || input.lastResult === "failed") {
    items.push({
      key: "h7-result",
      text:
        input.lastResult === "partial"
          ? "Son yürütme kısmi tamamlandı — tam sonuç değil."
          : "Son yürütme başarısız oldu.",
      tone: input.lastResult === "partial" ? "warn" : "danger",
      href: "#/",
    });
  }

  if (input.statsState === "error") {
    items.push({ key: "stats-unknown", text: unknownHint("Sistem istatistikleri"), tone: "neutral" });
  }
  if (input.runsState === "error") {
    items.push({
      key: "runs-unknown",
      text: "Kaynak koşuları alınamadı — durum bilinmiyor.",
      tone: "neutral",
      href: "#/sources",
    });
  }

  return items;
}

/* ── Sorgular + özet (tek okuma noktası) ──────────────────────────────── */

function useHealthSummary(): HealthSummary {
  const stats = useSystemStats();
  const runs = useSourceHealth();
  const coverage = useQuery({
    queryKey: ["source-coverage"],
    queryFn: () => api.get<SourceCoverageRow[]>("/sources/coverage"),
  });
  const feeds = useQuery({ queryKey: ["feeds"], queryFn: () => api.get<Feed[]>("/rss/feeds") });
  const rssStats = useQuery({ queryKey: ["rss-stats"], queryFn: () => api.get<RssStats>("/rss/stats") });
  const backup = useBackupStatus();
  const agent = useQuery({ queryKey: [AGENT_STATUS_KEY], queryFn: getAgentStatus });
  const vault = useQuery({ queryKey: [VAULT_STATUS_KEY], queryFn: getVaultStatus });
  const proactivity = useQuery({ queryKey: [PROACTIVITY_STATUS_KEY], queryFn: proactivityStatus });
  // Ayarlar'daki H7 özetiyle AYNI anahtar (aynı uca iki istek gitmez).
  const executions = useQuery({ queryKey: ["execution-plans", "recent"], queryFn: () => recentExecutionPlans(20) });

  const queries: { isError: boolean; isLoading: boolean; refetch: () => unknown }[] = [
    stats,
    runs,
    coverage,
    feeds,
    rssStats,
    backup,
    agent,
    vault,
    proactivity,
    executions,
  ];

  const coverageRows = coverage.data ?? [];
  const sourceProblems = coverageRows.filter((row) => isProblem(row));
  const feedRows = feeds.data ?? [];
  const feedAttention = feedRows.filter((feed) => feedStateView(feed).attention);
  const vaultView = describeVaultState(vault.data, vault.isError);
  const h4Row = agent.data?.local_cognition;
  const h4View = h4Row ? h4Summary(h4Row) : null;
  const plans = summarizeExecutionPlans(executions.data ?? []);
  const driveError = backup.data?.last_drive_error ?? null;
  const worker = workerStatusView(stats.data?.worker.status);

  /* Bilinemeyenler: istek düşen her bölüm buraya yazılır — sessizce atlanmaz. */
  const unknownSections: string[] = [];
  const noteUnknown = (isError: boolean, label: string) => {
    if (isError) unknownSections.push(label);
  };
  noteUnknown(stats.isError, "sistem istatistikleri");
  noteUnknown(coverage.isError, "kaynak kapsamı");
  noteUnknown(runs.isError, "kaynak koşuları");
  noteUnknown(feeds.isError, "RSS beslemeleri");
  noteUnknown(rssStats.isError, "RSS istatistikleri");
  noteUnknown(backup.isError, "yedek durumu");
  noteUnknown(agent.isError, "Brain Interface");
  noteUnknown(vault.isError, "bilgi kasası");
  noteUnknown(proactivity.isError, "proaktivite");
  noteUnknown(executions.isError, "H7 kararları");

  const vaultDegraded = vaultView.kind === "unavailable" || vaultView.kind === "read_only";
  const h4Degraded = Boolean(h4Row && h4Row.state !== "disabled" && h4Row.state !== "ready");
  const h7Pending = plans.pending > 0;
  const h7ResultDegraded = plans.last_result === "partial" || plans.last_result === "failed";
  // Yüklenirken hiçbir şey bilinmiyordur: sahte sıfır/yeşil gösterilmez (§33).
  const anyLoading = queries.some((query) => query.isLoading);

  const attention =
    sourceProblems.length > 0 ||
    feedAttention.length > 0 ||
    Boolean(driveError) ||
    vaultDegraded ||
    h4Degraded ||
    h7Pending ||
    h7ResultDegraded;

  const failingFeeds =
    rssStats.data?.failing_feeds ?? (rssStats.isError || feeds.isError ? null : feedAttention.length);

  const statsData = stats.data;
  const backupData = backup.data;
  const agentData = agent.data;
  const brain = agentData?.brain ?? null;

  return {
    statsState: dataState(stats),
    resourceHint: statsData ? resourceHint(statsData) : null,
    worker,
    coverageState: dataState(coverage),
    sourceTotal: coverageRows.length,
    sourceHealthy: coverageRows.filter((row) => row.last_status === "ok").length,
    sourceProblems,
    sourceNeverRan: coverageRows.filter((row) => !row.last_status).length,
    runningSources: (runs.data ?? []).filter((run) => run.status === "running").length,
    backupState: dataState(backup),
    lastBackupAt: backupData?.last_backup?.at ?? null,
    backupPendingChanges: backupData?.changes_since_backup ?? false,
    agentState: dataState(agent),
    brain,
    brainReadiness: brainReadiness(brain ?? undefined, agent.isError),
    h4: h4View,
    vaultState: dataState(vault),
    vault: vaultView,
    proactivityState: dataState(proactivity),
    proactivityEnabled: proactivity.data ? proactivity.data.enabled : null,
    executionsState: dataState(executions),
    plans,
    attentionItems: attentionItems({
      coverageState: dataState(coverage),
      sourceProblems,
      failingFeeds,
      rssStatsState: dataState(rssStats),
      feedsState: dataState(feeds),
      driveError,
      backupState: dataState(backup),
      statsState: dataState(stats),
      runsState: dataState(runs),
      vaultState: dataState(vault),
      vaultDegraded,
      vaultChip: vaultView.chip,
      agentState: dataState(agent),
      h4Degraded,
      h4Hint: h4View?.hint ?? null,
      h4Label: h4View?.label ?? "bilinmiyor",
      proactivityState: dataState(proactivity),
      executionsState: dataState(executions),
      pendingDecisions: plans.pending,
      lastResult: plans.last_result,
    }),
    unknownSections,
    overall: overallView(overallState({ unknown: unknownSections.length > 0 || anyLoading, attention })),
    bundle: buildDiagnosticsBundle({
      stats: { state: dataState(stats), data: statsData },
      coverage: { state: dataState(coverage), rows: coverageRows },
      runsState: dataState(runs),
      feeds: { state: dataState(feeds), rows: feedRows },
      rssStats: { state: dataState(rssStats), data: rssStats.data },
      backup: { state: dataState(backup), data: backupData },
      agent: { state: dataState(agent), brain, h4: h4View },
      vault: { state: dataState(vault), chip: vaultView.chip },
      proactivity: { state: dataState(proactivity), enabled: proactivity.data ? proactivity.data.enabled : null },
      executions: { state: dataState(executions), plans },
    }),
    loading: queries.some((query) => query.isLoading),
    retryUnknown: () => {
      for (const query of queries) {
        if (query.isError) void query.refetch();
      }
    },
  };
}

/* ── Tanılama paketi gövdesi ──────────────────────────────────────────── */

interface DiagnosticsParts {
  stats: { state: DataState; data: SystemStats | undefined };
  coverage: { state: DataState; rows: SourceCoverageRow[] };
  runsState: DataState;
  feeds: { state: DataState; rows: Feed[] };
  rssStats: { state: DataState; data: RssStats | undefined };
  backup: { state: DataState; data: BackupStatus | undefined };
  agent: { state: DataState; brain: BrainStatusView | null; h4: HealthSummary["h4"] };
  vault: { state: DataState; chip: string };
  proactivity: { state: DataState; enabled: boolean | null };
  executions: { state: DataState; plans: ExecutionSummary };
}

/** Bölüm adları UÇ adlarıdır: ajan tam olarak hangi isteğin düştüğünü görmeli. */
function buildDiagnosticsBundle(parts: DiagnosticsParts): string {
  const MISSING = "unknown — request failed";
  const unknown: string[] = [];
  const track = (state: DataState, endpoint: string) => {
    if (state === "error") unknown.push(endpoint);
  };
  track(parts.stats.state, "system/stats");
  track(parts.coverage.state, "sources/coverage");
  track(parts.runsState, "sources/health");
  track(parts.feeds.state, "rss/feeds");
  track(parts.rssStats.state, "rss/stats");
  track(parts.backup.state, "backup/status");
  track(parts.agent.state, "agent/status");
  track(parts.vault.state, "obsidian/status");
  track(parts.proactivity.state, "proactivity/status");
  track(parts.executions.state, "execution/plans");

  const ready = (state: DataState) => state === "ready" || state === "empty";
  /** Bölüm alanı: hata → "unknown — request failed", hazır → değer, henüz yok → "unknown". */
  const field = (state: DataState, value: () => string) =>
    state === "error" ? MISSING : ready(state) ? value() : "unknown";

  const stats = parts.stats.data;
  const backup = parts.backup.data;
  const plans = parts.executions.plans;
  const brainAvailable = [parts.agent.state, parts.vault.state, parts.proactivity.state, parts.executions.state].some(
    ready,
  );

  return formatSystemDiagnostics({
    generated_at: new Date().toISOString(),
    route: "Sistem Durumu (#/health)",
    runtime:
      !ready(parts.stats.state) || !stats
        ? null
        : {
            api: "ok",
            worker: workerStatusView(stats.worker.status).label,
            uptime: formatUptime(stats.uptime_s),
            cpu: stats.cpu_pct === null ? "not measured yet" : `${Math.round(stats.cpu_pct)}%`,
            memory:
              stats.mem_total_kb !== null && stats.mem_available_kb !== null
                ? `${formatGib(stats.mem_available_kb * 1024)} free / ${formatGib(stats.mem_total_kb * 1024)}`
                : null,
            disk: stats.disk ? `${formatGib(stats.disk.free)} free / ${formatGib(stats.disk.total)}` : null,
          },
    sources: ready(parts.coverage.state)
      ? {
          total: parts.coverage.rows.length,
          healthy: parts.coverage.rows.filter((row) => row.last_status === "ok").length,
          attention: parts.coverage.rows.filter((row) => isProblem(row)).length,
          problems: parts.coverage.rows.filter((row) => isProblem(row)).map(toProblemDiagnostic),
        }
      : null,
    rss:
      !ready(parts.feeds.state) || !ready(parts.rssStats.state) || !parts.rssStats.data
        ? null
        : {
            total: parts.rssStats.data.feeds,
            active: parts.rssStats.data.active_feeds,
            failing: parts.rssStats.data.failing_feeds,
            disabled: parts.feeds.rows.filter((feed) => !feed.active).length,
            errors: parts.feeds.rows
              .filter((feed) => feedStateView(feed).attention)
              .slice(0, 5)
              .map((feed) => `${feed.title}: ${feed.error_count} hata`),
          },
    backup:
      !ready(parts.backup.state) || !backup
        ? null
        : {
            last_backup_at: backup.last_backup?.at ?? null,
            last_backup_size: backup.last_backup ? formatBytes(backup.last_backup.size) : null,
            pending_changes: backup.changes_since_backup ? 1 : 0,
            drive_configured: Boolean(backup.drive_folder_id),
            last_drive_error: backup.last_drive_error?.message ?? null,
          },
    brain: brainAvailable
      ? {
          mcp: field(
            parts.agent.state,
            () =>
              `${parts.agent.brain?.server_name ?? "?"} · yerel sınır: ${
                parts.agent.brain?.loopback_only ? "yalnız 127.0.0.1" : "dışarıda"
              }`,
          ),
          tool_surface: field(parts.agent.state, () => `${parts.agent.brain?.tool_count ?? 0} sınırlı araç (H0 → H7)`),
          vault: field(parts.vault.state, () => parts.vault.chip),
          h4: field(parts.agent.state, () =>
            parts.agent.h4
              ? `${parts.agent.h4.label}${parts.agent.h4.hint ? ` — ${parts.agent.h4.hint}` : ""}`
              : "unknown",
          ),
          h6: field(parts.proactivity.state, () => (parts.proactivity.enabled ? "açık" : "kapalı")),
          h7: field(
            parts.executions.state,
            () => `${plans.pending} bekleyen karar; son sonuç: ${plans.last_result ?? "yok"}`,
          ),
        }
      : null,
    unknown,
  });
}

/* ── Gruplar ──────────────────────────────────────────────────────────── */

/** Bir kalemin değeri: okunamadıysa "durum bilinmiyor", yüklenirken "…". */
function stateText(state: DataState, ready: () => string): string {
  if (state === "error") return "durum bilinmiyor";
  if (state === "loading") return "…";
  return ready();
}

function OverviewGroup({ summary }: { summary: HealthSummary }) {
  const { statsState, coverageState, backupState, agentState, vaultState, proactivityState, executionsState } = summary;

  const sourcesValue = stateText(coverageState, () =>
    healthSummaryLabel({
      total: summary.sourceTotal,
      healthy: summary.sourceHealthy,
      attention: summary.sourceProblems.length,
    }),
  );
  const sourcesHint = [
    summary.sourceNeverRan > 0 ? `${summary.sourceNeverRan} kaynak hiç çalışmadı` : null,
    summary.runningSources > 0 ? `${summary.runningSources} kaynak şu an çekiliyor` : null,
  ]
    .filter((part): part is string => part !== null)
    .join(" · ");

  const backupValue = stateText(backupState, () =>
    summary.lastBackupAt ? relativeTime(summary.lastBackupAt) : "hiç yedek yok",
  );
  const brainValue = stateText(agentState, () => BRAIN_READINESS[summary.brainReadiness].label);
  const vaultValue = stateText(vaultState, () => summary.vault.chip);
  const h4Value = stateText(agentState, () => summary.h4?.label ?? "bilinmiyor");
  const h6Value = stateText(proactivityState, () => (summary.proactivityEnabled ? "açık" : "kapalı"));
  const h7Value = stateText(executionsState, () =>
    summary.plans.pending > 0 ? `${summary.plans.pending} bekleyen karar` : "bekleyen karar yok",
  );

  const h7Tone: StatusTone =
    executionsState === "error"
      ? "neutral"
      : summary.plans.pending > 0
        ? "warn"
        : summary.plans.last_result === "failed"
          ? "danger"
          : summary.plans.last_result === "partial"
            ? "warn"
            : "ok";

  return (
    <div>
      <SectionHeader
        label="Genel bakış"
        hint="skor değil; her kalem kendi kaynağından okunur"
        action={<Chip tone={summary.overall.tone}>{summary.overall.label}</Chip>}
      />
      <Section bodyClassName="grid gap-x-8 md:grid-cols-2">
        <div>
          <p className="mb-1 text-micro text-muted">Sistem ve veri</p>
          <SummaryRow
            label="API ve çalışma zamanı"
            value={stateText(statsState, () => "çalışıyor")}
            tone={statsState === "ready" ? "ok" : "neutral"}
            hint={statsState === "error" ? unknownHint("Sistem istatistikleri") : summary.resourceHint}
          />
          <SummaryRow
            label="Worker"
            value={statsState === "error" ? "bilinmiyor" : summary.worker.label}
            tone={statsState === "error" ? "neutral" : summary.worker.tone}
            hint={statsState === "error" ? unknownHint("Worker durumu") : summary.worker.hint}
          />
          <SummaryRow
            label="Kaynaklar"
            value={sourcesValue}
            tone={
              coverageState === "ready" || coverageState === "empty"
                ? summary.sourceProblems.length > 0
                  ? "warn"
                  : "ok"
                : "neutral"
            }
            hint={coverageState === "error" ? unknownHint("Kaynak kapsamı") : sourcesHint || null}
            href="#/sources"
          />
          <SummaryRow
            label="Yedekleme"
            value={backupValue}
            tone={backupState === "ready" && summary.lastBackupAt ? "ok" : "neutral"}
            hint={
              backupState === "error"
                ? unknownHint("Yedek durumu")
                : summary.lastBackupAt
                  ? summary.backupPendingChanges
                    ? "son yedekten beri bekleyen değişiklik var"
                    : "son yedekten beri değişiklik yok"
                  : '"Şimdi yedekle" ile başla.'
            }
          />
        </div>

        <div>
          <p className="mb-1 text-micro text-muted">Zihin katmanı</p>
          <SummaryRow
            label="Brain Interface"
            value={brainValue}
            tone={agentState === "error" ? "neutral" : BRAIN_READINESS[summary.brainReadiness].tone}
            hint={
              agentState === "error"
                ? unknownHint("Brain Interface durumu")
                : summary.brain
                  ? `${summary.brain.server_name} · ${summary.brain.tool_count} sınırlı araç`
                  : null
            }
          />
          <SummaryRow
            label="f0rknbrain"
            value={vaultValue}
            tone={vaultState === "error" ? "neutral" : VAULT_TONE[summary.vault.kind]}
            hint={vaultState === "error" ? unknownHint("Bilgi kasası durumu") : summary.vault.hint}
            href="#/notes"
          />
          <SummaryRow
            label="H4 · yerel biliş"
            value={h4Value}
            tone={agentState === "error" ? "neutral" : (summary.h4?.tone ?? "neutral")}
            hint={agentState === "error" ? unknownHint("H4 durumu") : summary.h4?.hint}
          />
          <SummaryRow
            label="H6 · proaktivite"
            value={h6Value}
            tone={proactivityState === "error" ? "neutral" : summary.proactivityEnabled ? "ok" : "neutral"}
            hint={
              proactivityState === "error"
                ? unknownHint("Proaktivite durumu")
                : summary.proactivityEnabled === false
                  ? "Kapalı olması hata değil: H6 yalnız dikkat gerektiren durumlarda konuşur."
                  : null
            }
          />
          <SummaryRow
            label="H7 · kararlar"
            value={h7Value}
            tone={h7Tone}
            hint={
              executionsState === "error"
                ? unknownHint("H7 karar özeti")
                : summary.plans.last_result === "partial"
                  ? "Son yürütme kısmi tamamlandı."
                  : summary.plans.last_result === "failed"
                    ? "Son yürütme başarısız oldu."
                    : null
            }
            href="#/"
          />
          <p className="pt-2 text-micro text-muted">
            forkOS yalnız kendi MCP sunucusunun hazır olduğunu bilir; Hermes istemcisinin bağlı olduğunu doğrulayamaz.{" "}
            <a href="#/settings?tab=brain" className="text-accent hover:underline">
              Brain &amp; Agent ayarları →
            </a>
          </p>
        </div>
      </Section>
    </div>
  );
}

function AttentionGroup({ summary }: { summary: HealthSummary }) {
  const items = summary.attentionItems;
  return (
    <div>
      <SectionHeader
        label="İlgi gerekenler"
        hint={items.length === 0 ? "temiz" : `${items.length} kalem`}
        action={
          summary.unknownSections.length > 0 ? (
            <Button variant="ghost" size="sm" onClick={summary.retryUnknown}>
              <RefreshCw size={13} aria-hidden="true" /> Yeniden dene
            </Button>
          ) : undefined
        }
      />
      <Section>
        {items.length === 0 ? (
          <p className="text-meta text-muted">
            İlgi gereken bir şey yok: bütün kalemler okunabildi ve sorun bildirmiyor.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {items.map((item) => (
              <li key={item.key} className="flex items-start gap-2 text-meta">
                <span
                  className={cx("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", TONE_DOT[item.tone])}
                  aria-hidden="true"
                />
                {item.href ? (
                  <a href={item.href} className={cx("min-w-0 hover:underline", TONE_TEXT[item.tone])}>
                    {item.text}
                  </a>
                ) : (
                  <span className={cx("min-w-0", TONE_TEXT[item.tone])}>{item.text}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}

/* ── Sayfa ────────────────────────────────────────────────────────────── */

export function HealthPage() {
  const summary = useHealthSummary();

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Sistem"
          title="Sistem Durumu"
          hint="Kaynaklar, beslemeler, yedekler ve zihin katmanı"
          action={
            <CopyButton
              text={summary.bundle}
              label="Teşhisi kopyala"
              ariaLabel="Agent için durum paketini kopyala"
              disabled={summary.loading}
              toastLabel="Sistem teşhisi panoya kopyalandı."
            />
          }
        />
        <WorkspaceScrollArea className="p-3">
          <div className="space-y-6">
            <SetupChecklist />
            <OverviewGroup summary={summary} />
            <AttentionGroup summary={summary} />
            <div>
              <SectionHeader label="Ayrıntılı sağlık" hint="kaynaklar · beslemeler · yedek · servis" />
              <div className="grid items-start gap-4 xl:grid-cols-2">
                {DETAIL_WIDGETS.map(({ name, component: Widget }) => (
                  <Widget key={name} />
                ))}
              </div>
            </div>
          </div>
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
