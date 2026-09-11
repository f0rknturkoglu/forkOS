/**
 * Kaynaklar çalışma alanı: katalog, sağlık, yenileme ve disk kullanımı.
 *
 * Bu ekran kaynakların "sessiz ölüm"ünü görünür kılar: üst üste boş koşan
 * kaynak, hata sınıfı, son görülme ve kapsam burada tek yerde durur.
 */

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, RefreshCw, Search } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { sourceLabel } from "@/core/labels";
import {
  Button,
  Chip,
  Empty,
  Input,
  Metric,
  MetricStrip,
  Section,
  Spinner,
  cx,
  relativeTime,
  useToast,
} from "@/core/ui";
import type {
  SourceCachePruneResult,
  SourceCacheStats,
  SourceCoverageRow,
  SourceHealth,
  SourceRefreshResult,
  SourceSyncStatus,
} from "@/core/types";
import { confirmDialog } from "@/core/dialog";

interface CatalogEntry {
  id: string;
  interval_minutes: number;
  kind: string;
  category?: string | null;
  /** Backend kaynak sınıfı: critical | normal | slow_optin (varsa). */
  class?: string | null;
  source_class?: string | null;
  estimated_seconds?: number | null;
}

const KIND_LABELS: Record<string, string> = { job: "İş ilanı", announcement: "Duyuru" };

const CLASS_LABELS: Record<string, string> = {
  critical: "Kritik",
  normal: "Normal",
  slow_optin: "Yavaş / isteğe bağlı",
};

type ChipTone = "ok" | "warn" | "danger" | "neutral" | "accent";

const STATUS_TONES: Record<string, ChipTone> = {
  ok: "ok",
  empty: "warn",
  error: "danger",
  running: "accent",
  abandoned: "neutral",
  queued: "neutral",
};

/** Kaynak sınıfı yoksa kimliğinden çıkar (LinkedIn opt-in, EURES yavaş). */
function classOf(entry: CatalogEntry): string {
  const explicit = entry.source_class ?? entry.class;
  if (explicit) return explicit;
  const id = entry.id.toLocaleLowerCase("tr");
  if (id.includes("linkedin") || id.includes("eures")) return "slow_optin";
  if (id.startsWith("jobhunter:") && id.includes(":")) return "critical";
  if (["ylsy", "osym", "yok"].some((official) => id === official)) return "critical";
  return "normal";
}

function formatBytes(value: number): string {
  if (value >= 1024 ** 3) return `${(value / 1024 ** 3).toFixed(1)} GB`;
  if (value >= 1024 ** 2) return `${(value / 1024 ** 2).toFixed(1)} MB`;
  if (value >= 1024) return `${(value / 1024).toFixed(0)} KB`;
  return `${value} B`;
}

export function SourcesWorkspace() {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [onlyProblems, setOnlyProblems] = useState(false);
  const [pending, setPending] = useState<Set<string>>(new Set());

  const catalog = useQuery({
    queryKey: ["source-catalog"],
    queryFn: () => api.get<CatalogEntry[]>("/sources/catalog"),
  });
  const runs = useQuery({
    queryKey: ["source-runs"],
    queryFn: () => api.get<SourceHealth[]>("/sources/runs"),
  });
  const sync = useQuery({
    queryKey: ["source-sync"],
    queryFn: () => api.get<SourceSyncStatus>("/sources/sync"),
    refetchInterval: (query) => (query.state.data?.running.length ? 2_000 : 30_000),
  });

  const refresh = useMutation({
    mutationFn: (body: { mode?: "general" | "full"; source_ids?: string[] }) =>
      api.post<SourceRefreshResult>("/sources/refresh", body),
    onSuccess: (result) => {
      invalidateAfter("source.sync");
      toast.push(
        result.queued ? `${result.queued} kaynak kuyruğa alındı` : "Seçilen kaynaklar aktif çekimde zaten var",
        { tone: "ok" },
      );
      setPending(new Set());
    },
  });

  const cache = useQuery({
    queryKey: ["source-cache"],
    queryFn: () => api.get<SourceCacheStats>("/sources/cache"),
  });
  const coverage = useQuery({
    queryKey: ["source-coverage"],
    queryFn: () => api.get<SourceCoverageRow[]>("/sources/coverage"),
  });
  const pruneCache = useMutation({
    mutationFn: () => api.post<SourceCachePruneResult>("/sources/cache/prune", {}),
    onSuccess: (result) => {
      void cache.refetch();
      toast.push(`${result.removed} dosya silindi · ${formatBytes(result.bytes_freed)} boşaltıldı`, { tone: "ok" });
    },
  });
  const clearCache = useMutation({
    mutationFn: () => api.post<SourceCachePruneResult>("/sources/cache/clear", { confirm: true }),
    onSuccess: (result) => {
      void cache.refetch();
      toast.push(`${result.removed} önbellek dosyası silindi`, { tone: "ok" });
    },
  });
  async function confirmClearCache() {
    const confirmed = await confirmDialog({
      title: "Kaynak önbelleği temizlensin mi?",
      body: `${cache.data?.files ?? 0} dosya (${formatBytes(cache.data?.bytes ?? 0)}) silinecek. Bu yalnızca disk önbelleğidir; hiçbir kayıt, not veya başvuru silinmez.`,
      confirmLabel: "Önbelleği temizle",
      tone: "danger",
    });
    if (confirmed) clearCache.mutate();
  }

  const entries = catalog.data ?? [];
  const latestBySource = useMemo(() => {
    const map = new Map<string, SourceHealth>();
    for (const run of runs.data ?? []) if (!map.has(run.source)) map.set(run.source, run);
    return map;
  }, [runs.data]);

  const running = useMemo(() => new Set((sync.data?.running ?? []).map((item) => item.source)), [sync.data]);

  /** Üst üste boş/hata koşan kaynaklar — sessiz ölüm göstergesi. */
  const problemSources = useMemo(() => {
    const recent = new Map<string, string[]>();
    const sorted = [...(runs.data ?? [])].sort((left, right) =>
      (right.started_at ?? "").localeCompare(left.started_at ?? ""),
    );
    for (const run of sorted) {
      const list = recent.get(run.source) ?? [];
      if (list.length < 4) list.push(run.status);
      recent.set(run.source, list);
    }
    const problems = new Set<string>();
    for (const [source, statuses] of recent) {
      const [latest, ...rest] = statuses;
      if (!latest) continue;
      if (latest === "error") problems.add(source);
      // "empty" tek başına hata değil; üst üste üç boş koşu bildirim eşiğidir.
      else if (latest === "empty" && rest.slice(0, 3).every((status) => status === "empty")) {
        problems.add(source);
      }
    }
    return problems;
  }, [runs.data]);

  const visible = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase("tr");
    return entries
      .filter((entry) => (onlyProblems ? problemSources.has(entry.id) : true))
      .filter((entry) => (needle ? entry.id.toLocaleLowerCase("tr").includes(needle) : true))
      .sort((left, right) => classOf(left).localeCompare(classOf(right)) || left.id.localeCompare(right.id));
  }, [entries, search, onlyProblems, problemSources]);

  const criticalCount = entries.filter((entry) => classOf(entry) === "critical").length;
  const optInCount = entries.filter((entry) => classOf(entry) === "slow_optin").length;
  const regularCount = entries.length - criticalCount - optInCount;
  // Tahmin: kaynak başına ~10 sn ortalama; kullanıcıya "yaklaşık" olarak yazılır.
  const estimateSeconds = (count: number) => Math.round(count * 10);

  function refreshOne(id: string) {
    setPending((current) => new Set(current).add(id));
    refresh.mutate({ source_ids: [id] });
  }

  function refreshStandard() {
    refresh.mutate({ mode: "general" });
  }

  if (catalog.isPending) {
    return (
      <div className="flex items-center gap-2 p-6 text-meta text-muted">
        <Spinner /> Kaynak kataloğu yükleniyor…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <MetricStrip>
        <Metric label="Kaynak" value={entries.length} hint={`${criticalCount} kritik · ${regularCount} normal`} />
        <Metric label="İsteğe bağlı" value={optInCount} hint="Genel yenilemeye girmez (ör. LinkedIn)" />
        <Metric label="Şu an çekilen" value={running.size} />
        <Metric label="Sorunlu" value={problemSources.size} hint="Üst üste boş veya hata" />
      </MetricStrip>

      <Section
        title="Yenileme"
        hint="Genel yenileme önce kritik kaynakları, sonra normal kaynakları çalıştırır; isteğe bağlı kaynaklar (LinkedIn) kendiliğinden çalışmaz."
      >
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="primary"
            disabled={refresh.isPending}
            onClick={refreshStandard}
            title={`${criticalCount + regularCount} kaynak · yaklaşık ${estimateSeconds(
              criticalCount + regularCount,
            )} sn`}
          >
            <RefreshCw size={14} /> Kritik ve normal kaynakları yenile
          </Button>
          <span className="text-meta text-muted">
            {criticalCount + regularCount} kaynak · yaklaşık {estimateSeconds(criticalCount + regularCount)} sn
          </span>
          <Button
            disabled={refresh.isPending}
            onClick={() => refresh.mutate({ mode: "full" })}
            title={`${entries.length} kaynak · yaklaşık ${estimateSeconds(entries.length)} sn`}
          >
            Tümünü tara ({entries.length} kaynak · ~{estimateSeconds(entries.length)} sn)
          </Button>
        </div>
        {sync.data?.active && (
          <p className="mt-2 text-meta text-muted" aria-live="polite">
            Aktif parti: {sync.data.active.completed_sources}/{sync.data.active.total_sources} kaynak ·{" "}
            {sync.data.active.items_found} yeni kayıt · durum {sync.data.active.status}
          </p>
        )}
      </Section>

      <Section title="Kaynak kataloğu">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <div className="relative min-w-0 flex-[1_1_16rem]">
            <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-icon" />
            <Input
              value={search}
              onChange={setSearch}
              placeholder="Kaynak ara…"
              ariaLabel="Kaynak ara"
              className="w-full pl-9"
            />
          </div>
          <Button
            size="sm"
            variant={onlyProblems ? "secondary" : "ghost"}
            onClick={() => setOnlyProblems((current) => !current)}
          >
            <AlertTriangle size={12} /> Yalnızca sorunlular
          </Button>
        </div>

        {visible.length === 0 ? (
          <Empty title="Eşleşen kaynak yok">Arama ölçütünü değiştirip yeniden dene.</Empty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[46rem] border-collapse text-meta">
              <thead>
                <tr className="border-b border-subtle text-left text-muted">
                  <th className="px-2 py-2 font-medium">Kaynak</th>
                  <th className="px-2 py-2 font-medium">Sınıf</th>
                  <th className="px-2 py-2 font-medium">Tür</th>
                  <th className="px-2 py-2 font-medium">Son çalışma</th>
                  <th className="px-2 py-2 font-medium">Durum</th>
                  <th className="px-2 py-2 font-medium">Kayıt</th>
                  <th className="px-2 py-2" />
                </tr>
              </thead>
              <tbody>
                {visible.map((entry) => {
                  const run = latestBySource.get(entry.id);
                  const busy = running.has(entry.id);
                  const sourceClass = classOf(entry);
                  return (
                    <tr key={entry.id} className="border-b border-subtle last:border-b-0">
                      <td className="px-2 py-2">
                        <span className="block truncate text-primary">{sourceLabel(entry.id)}</span>
                        <span className="block truncate text-micro text-muted">{entry.id}</span>
                      </td>
                      <td className="px-2 py-2">
                        <Chip tone={sourceClass === "slow_optin" ? "warn" : "neutral"}>
                          {CLASS_LABELS[sourceClass] ?? sourceClass}
                        </Chip>
                      </td>
                      <td className="px-2 py-2 text-secondary">
                        {KIND_LABELS[entry.kind] ?? entry.kind}
                        {entry.category ? ` · ${entry.category}` : ""}
                      </td>
                      <td className="px-2 py-2 tabular-nums text-secondary">
                        {busy ? "çekiliyor…" : run?.started_at ? relativeTime(run.started_at) : "hiç çalışmadı"}
                      </td>
                      <td className="px-2 py-2">
                        {busy ? (
                          <Chip tone="accent">çekiliyor</Chip>
                        ) : run ? (
                          <Chip tone={STATUS_TONES[run.status] ?? "neutral"}>{run.status}</Chip>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>
                      <td className="px-2 py-2 tabular-nums text-secondary">
                        {run?.items_found ? `+${run.items_found}` : "0"}
                      </td>
                      <td className="px-2 py-2 text-right">
                        <Button size="sm" disabled={busy || pending.has(entry.id)} onClick={() => refreshOne(entry.id)}>
                          Yenile
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section
        title="Kaynak sağlığı"
        hint="Bir kaynak üst üste üç kez boş dönerse bildirim üretilir; hata ve boş sonuç ayrı sayılır."
      >
        {problemSources.size === 0 ? (
          <p className="flex items-center gap-2 text-meta text-ok">
            <CheckCircle2 size={14} /> Sorunlu kaynak yok.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {[...problemSources].map((source) => {
              const run = latestBySource.get(source);
              return (
                <li
                  key={source}
                  className={cx(
                    "flex flex-wrap items-center gap-2 rounded-control border px-3 py-2 text-meta",
                    run?.status === "error"
                      ? "border-danger/40 bg-danger-surface text-danger"
                      : "border-warn/40 bg-warn-surface text-warn",
                  )}
                >
                  <span className="font-medium">{sourceLabel(source)}</span>
                  <Chip tone={run?.status === "error" ? "danger" : "warn"}>{run?.status ?? "—"}</Chip>
                  {run?.error && <span className="min-w-0 truncate opacity-90">{run.error}</span>}
                  <span className="ml-auto text-micro opacity-80">
                    {run?.started_at ? relativeTime(run.started_at) : ""}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </Section>

      <Section title="Son koşular">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[38rem] border-collapse text-meta">
            <thead>
              <tr className="border-b border-subtle text-left text-muted">
                <th className="px-2 py-2 font-medium">Kaynak</th>
                <th className="px-2 py-2 font-medium">Durum</th>
                <th className="px-2 py-2 font-medium">Başlangıç</th>
                <th className="px-2 py-2 font-medium">Kayıt</th>
                <th className="px-2 py-2 font-medium">Hata</th>
              </tr>
            </thead>
            <tbody>
              {(runs.data ?? []).slice(0, 40).map((run) => (
                <tr key={`${run.source}:${run.started_at}`} className="border-b border-subtle last:border-b-0">
                  <td className="px-2 py-2">
                    <span className="block truncate text-primary">{sourceLabel(run.source)}</span>
                  </td>
                  <td className="px-2 py-2">
                    <Chip tone={STATUS_TONES[run.status] ?? "neutral"}>{run.status}</Chip>
                  </td>
                  <td className="px-2 py-2 tabular-nums text-secondary">
                    {run.started_at ? relativeTime(run.started_at) : "—"}
                  </td>
                  <td className="px-2 py-2 tabular-nums text-secondary">{run.items_found}</td>
                  <td className="max-w-[18rem] truncate px-2 py-2 text-danger">{run.error ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section
        title="Kapsam matrisi"
        hint="Hangi kurumu takip ediyoruz, hangisi eksik? Resmî kaynak merkezî kayıttır; kurum siteleri erken sinyal verir."
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[52rem] border-collapse text-meta">
            <thead>
              <tr className="border-b border-subtle text-left text-muted">
                <th className="px-2 py-2 font-medium">Kurum / kaynak</th>
                <th className="px-2 py-2 font-medium">Güven</th>
                <th className="px-2 py-2 font-medium">Tür</th>
                <th className="px-2 py-2 font-medium">Son başarılı</th>
                <th className="px-2 py-2 font-medium">Son yeni içerik</th>
                <th className="px-2 py-2 font-medium">Ort. aralık</th>
                <th className="px-2 py-2 font-medium">Üst üste boş</th>
                <th className="px-2 py-2 font-medium">Durum</th>
                <th className="px-2 py-2 font-medium">Son hata</th>
              </tr>
            </thead>
            <tbody>
              {(coverage.data ?? []).map((row) => (
                <tr key={row.source} className="border-b border-subtle last:border-b-0">
                  <td className="px-2 py-2">
                    <span className="block truncate text-primary">{sourceLabel(row.source)}</span>
                    <span className="block truncate text-micro text-muted">{row.url ?? row.source}</span>
                  </td>
                  <td className="px-2 py-2">
                    {row.official === null ? (
                      <span className="text-muted">—</span>
                    ) : (
                      <Chip tone={row.official ? "ok" : "neutral"}>{row.official ? "Resmî" : "İkincil"}</Chip>
                    )}
                  </td>
                  <td className="px-2 py-2 text-secondary">
                    {KIND_LABELS[row.kind] ?? row.kind}
                    {row.parser_version ? ` · ${row.parser_version}` : ""}
                  </td>
                  <td className="px-2 py-2 tabular-nums text-secondary">
                    {row.last_success_at ? relativeTime(row.last_success_at) : "hiç"}
                  </td>
                  <td className="px-2 py-2 tabular-nums text-secondary">
                    {row.last_new_content_at ? relativeTime(row.last_new_content_at) : "yok"}
                  </td>
                  <td className="px-2 py-2 tabular-nums text-secondary">
                    {row.avg_publish_interval_days === null ? "—" : `${row.avg_publish_interval_days} gün`}
                  </td>
                  <td className="px-2 py-2 tabular-nums text-secondary">{row.consecutive_empty}</td>
                  <td className="px-2 py-2">
                    {row.circuit_open ? (
                      <Chip tone="danger">devre açık</Chip>
                    ) : row.consecutive_empty >= 3 ? (
                      <Chip tone="warn">sessiz</Chip>
                    ) : (
                      <Chip tone={row.last_status ? (STATUS_TONES[row.last_status] ?? "neutral") : "neutral"}>
                        {row.last_status ?? "hiç çalışmadı"}
                      </Chip>
                    )}
                  </td>
                  <td className="max-w-[16rem] truncate px-2 py-2 text-danger">
                    {row.last_error ? `${row.last_error_kind ?? ""} ${row.last_error}`.trim() : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section
        title="Disk önbelleği"
        hint="Kaynak yanıtları sınırlı bir bütçeyle saklanır; temizlik yalnızca disk önbelleğine dokunur, PostgreSQL kayıtlarına asla."
      >
        {cache.isPending ? (
          <p className="text-meta text-muted">Önbellek ölçülüyor…</p>
        ) : (
          <>
            <MetricStrip>
              <Metric label="Boyut" value={formatBytes(cache.data?.bytes ?? 0)} />
              <Metric label="Dosya" value={cache.data?.files ?? 0} />
              <Metric label="En eski" value={cache.data?.oldest ? relativeTime(cache.data.oldest) : "—"} />
              <Metric
                label="Bütçe"
                value={formatBytes(cache.data?.max_bytes ?? 0)}
                hint={`TTL ${Math.round((cache.data?.max_age_seconds ?? 0) / 86400)} gün`}
              />
            </MetricStrip>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Button disabled={pruneCache.isPending} onClick={() => pruneCache.mutate()}>
                <RefreshCw size={13} /> Bütçeye indir (TTL + LRU)
              </Button>
              <Button variant="danger" disabled={clearCache.isPending} onClick={() => void confirmClearCache()}>
                Önbelleği temizle
              </Button>
              <span className="text-meta text-muted">Önbellek modu: {cache.data?.mode ?? "off"}</span>
            </div>
          </>
        )}
      </Section>
    </div>
  );
}
