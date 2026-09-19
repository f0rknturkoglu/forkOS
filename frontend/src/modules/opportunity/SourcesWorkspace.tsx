/**
 * Kaynaklar çalışma alanı: katalog, sağlık, yenileme ve disk kullanımı.
 *
 * Bu ekran kaynakların "sessiz ölüm"ünü görünür kılar: üst üste boş koşan
 * kaynak, hata sınıfı, son görülme ve kapsam burada tek yerde durur. Aynı
 * bilgiyi Sistem Sağlığı > Kaynaklar yüzeyi de gösterir; burası kanonik
 * (tam) yüzdür, orası yalnızca özet.
 *
 * Sağlık kararı istemcide son koşular dilimlenerek ÜRETİLMEZ: eşikler ve
 * özetler backend'den (/sources/coverage) gelir, burası yalnızca gösterir.
 */

import { useMemo, useState } from "react";
import { SOURCE_SYNC_ACTIVE_MS, SOURCE_SYNC_IDLE_MS } from "@/core/SyncProgress";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, RefreshCw, Search } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { sourceLabel } from "@/core/labels";
import { sourceSyncStatusLabel, sourceSyncStatusTone, SyncProgress } from "@/core/SyncProgress";
import {
  Button,
  Chip,
  Empty,
  FilterChip,
  IconButton,
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
import { useOnline } from "@/lib/hooks";

interface CatalogEntry {
  id: string;
  interval_minutes: number;
  kind: string;
  category?: string | null;
  /** Backend kaynak sınıfı: critical | normal | slow_optin. */
  class?: string | null;
  /** Kaynağın kendi verdiği kaba süre tahmini (saniye). */
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
  partial: "warn",
  error: "danger",
  running: "accent",
  abandoned: "neutral",
  disabled: "neutral",
  queued: "neutral",
};

function formatBytes(value: number): string {
  if (value >= 1024 ** 3) return `${(value / 1024 ** 3).toFixed(1)} GB`;
  if (value >= 1024 ** 2) return `${(value / 1024 ** 2).toFixed(1)} MB`;
  if (value >= 1024) return `${(value / 1024).toFixed(0)} KB`;
  return `${value} B`;
}

/** Kaba süre tahmini; katalogdaki `estimated_seconds` toplanarak gösterilir. */
function formatSeconds(seconds: number): string {
  if (seconds < 60) return `${seconds} sn`;
  const minutes = Math.round(seconds / 60);
  return minutes < 60 ? `${minutes} dk` : `${Math.round(minutes / 60)} sa`;
}

export function SourcesWorkspace() {
  const online = useOnline();
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
    refetchInterval: (query) => (query.state.data?.active ? SOURCE_SYNC_ACTIVE_MS : SOURCE_SYNC_IDLE_MS),
  });
  const coverage = useQuery({
    queryKey: ["source-coverage"],
    queryFn: () => api.get<SourceCoverageRow[]>("/sources/coverage"),
  });
  const cache = useQuery({
    queryKey: ["source-cache"],
    queryFn: () => api.get<SourceCacheStats>("/sources/cache"),
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
    },
    // Hata sonrası satır düğmeleri kilitli kalmasın: pending her durumda temizlenir.
    onSettled: () => setPending(new Set()),
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
  const currentBySource = useMemo(
    () => new Map((sync.data?.sources ?? []).map((item) => [item.source, item])),
    [sync.data],
  );

  /**
   * Sorunlu kaynaklar — "sessiz ölüm" göstergesi. Karar backend özetinden
   * (/sources/coverage) gelir: devre kesici açık, son koşu hata ya da üst üste
   * üç boş koşu. İstemci son N koşuyu dilimleyip eşik hesaplamaz.
   */
  const problems = useMemo(
    () =>
      (coverage.data ?? [])
        .filter((row) => row.circuit_open || row.last_status === "error" || row.consecutive_empty >= 3)
        .sort((left, right) => left.source.localeCompare(right.source)),
    [coverage.data],
  );
  const problemSources = useMemo(() => new Set(problems.map((row) => row.source)), [problems]);

  const visible = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase("tr");
    return entries
      .filter((entry) => (onlyProblems ? problemSources.has(entry.id) : true))
      .filter((entry) => (needle ? entry.id.toLocaleLowerCase("tr").includes(needle) : true))
      .sort(
        (left, right) =>
          (left.class ?? "normal").localeCompare(right.class ?? "normal") || left.id.localeCompare(right.id),
      );
  }, [entries, search, onlyProblems, problemSources]);

  const criticalCount = entries.filter((entry) => (entry.class ?? "normal") === "critical").length;
  const optInCount = entries.filter((entry) => (entry.class ?? "normal") === "slow_optin").length;
  const regularCount = entries.length - criticalCount - optInCount;
  // "Kritik ve normal" kapsamı: isteğe bağlı/yavaş kaynaklar genel yenilemeye girmez.
  const generalSources = entries.filter((entry) => (entry.class ?? "normal") !== "slow_optin");
  // Süre tahmini kaynak kataloğundaki `estimated_seconds` toplamıdır (backend alanı).
  const generalSeconds = generalSources.reduce((total, entry) => total + (entry.estimated_seconds ?? 0), 0);
  const fullSeconds = entries.reduce((total, entry) => total + (entry.estimated_seconds ?? 0), 0);

  function refreshOne(id: string) {
    setPending((current) => new Set(current).add(id));
    refresh.mutate({ source_ids: [id] });
  }

  function refreshStandard() {
    refresh.mutate({ mode: "general" });
  }

  if (catalog.isPending) {
    return <Spinner label="Kaynak kataloğu yükleniyor…" />;
  }

  if (catalog.isError) {
    return (
      <Empty
        variant="page"
        title="Kaynak kataloğu yüklenemedi"
        action={
          <Button size="sm" onClick={() => void catalog.refetch()}>
            Yeniden dene
          </Button>
        }
      >
        Katalog alınamadı; bu "kaynak yok" demek değil. Bağlantı gelince yeniden dene.
      </Empty>
    );
  }

  return (
    <div className="space-y-4">
      <MetricStrip>
        <Metric label="Kaynak" value={entries.length} hint={`${criticalCount} kritik · ${regularCount} normal`} />
        <Metric label="İsteğe bağlı" value={optInCount} hint="Genel yenilemeye girmez (ör. LinkedIn)" />
        <Metric
          label="Şu an çekilen"
          value={sync.isError ? "—" : running.size}
          hint={sync.isError ? "durum alınamadı" : undefined}
        />
        <Metric
          label="Sorunlu"
          value={coverage.isPending ? "…" : coverage.isError ? "—" : problemSources.size}
          hint="Devre kesici, hata ya da üst üste boş"
        />
      </MetricStrip>

      <Section
        title="Yenileme"
        hint="Genel yenileme önce kritik kaynakları, sonra normal kaynakları çalıştırır; isteğe bağlı kaynaklar (LinkedIn) kendiliğinden çalışmaz."
      >
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="primary"
            disabled={!online || refresh.isPending}
            onClick={refreshStandard}
            title={`${generalSources.length} kaynak · yaklaşık ${formatSeconds(generalSeconds)}`}
          >
            <RefreshCw size={14} /> Kritik ve normal kaynakları yenile
          </Button>
          <span className="text-meta text-muted">
            {generalSources.length} kaynak · yaklaşık {formatSeconds(generalSeconds)}
          </span>
          <Button
            disabled={!online || refresh.isPending}
            onClick={() => refresh.mutate({ mode: "full" })}
            title={`${entries.length} kaynak · yaklaşık ${formatSeconds(fullSeconds)}`}
          >
            Tümünü tara ({entries.length} kaynak · {formatSeconds(fullSeconds)})
          </Button>
        </div>
        {!online && (
          <p className="mt-2 text-meta text-warn" role="status">
            Çevrimdışı: yenileme başlatılamaz. Kayıtlı veriler okunmaya devam eder.
          </p>
        )}
        <div className="mt-3">
          <SyncProgress />
        </div>
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
          <FilterChip
            label="Yalnızca sorunlular"
            count={problemSources.size}
            active={onlyProblems}
            icon={<AlertTriangle size={12} />}
            onClick={() => setOnlyProblems((current) => !current)}
          />
        </div>

        {visible.length === 0 ? (
          onlyProblems && coverage.isError ? (
            <Empty title="Sağlık verisi yok">
              Sağlık özeti alınamadığı için "yalnızca sorunlular" süzgeci uygulanamıyor.
            </Empty>
          ) : (
            <Empty title="Eşleşen kaynak yok">Arama ölçütünü değiştirip yeniden dene.</Empty>
          )
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[52rem] border-collapse text-meta">
              <thead>
                <tr className="border-b border-subtle text-left text-muted">
                  <th className="px-2 py-2 font-medium">Kaynak</th>
                  <th className="px-2 py-2 font-medium">Sınıf</th>
                  <th className="px-2 py-2 font-medium">Tür</th>
                  <th className="px-2 py-2 font-medium">Tahmini süre</th>
                  <th className="px-2 py-2 font-medium">Son çalışma</th>
                  <th className="px-2 py-2 font-medium">Durum</th>
                  <th className="px-2 py-2 font-medium">Kayıt</th>
                  <th className="px-2 py-2" />
                </tr>
              </thead>
              <tbody>
                {visible.map((entry) => {
                  const run = latestBySource.get(entry.id);
                  const current = currentBySource.get(entry.id);
                  const busy = current?.status === "running" || current?.status === "queued";
                  const shownStatus = current?.status ?? run?.status;
                  const shownItems = current?.items_found ?? run?.items_found ?? 0;
                  const sourceClass = entry.class ?? "normal";
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
                        {entry.estimated_seconds ? formatSeconds(entry.estimated_seconds) : "—"}
                      </td>
                      <td className="px-2 py-2 tabular-nums text-secondary">
                        {current?.status === "running"
                          ? "çekiliyor…"
                          : current?.status === "queued"
                            ? "kuyrukta"
                            : current?.finished_at
                              ? relativeTime(current.finished_at)
                              : run?.started_at
                                ? relativeTime(run.started_at)
                                : "hiç çalışmadı"}
                      </td>
                      <td className="px-2 py-2">
                        {current ? (
                          <Chip tone={sourceSyncStatusTone(current.status)}>
                            {sourceSyncStatusLabel(current.status)}
                          </Chip>
                        ) : run ? (
                          <Chip tone={STATUS_TONES[run.status] ?? "neutral"}>{run.status}</Chip>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>
                      <td className={cx("px-2 py-2 tabular-nums", shownItems > 0 ? "text-ok" : "text-secondary")}>
                        {shownItems > 0 ? `+${shownItems}` : "0"}
                      </td>
                      <td className="px-2 py-2 text-right">
                        <IconButton
                          title={`${sourceLabel(entry.id)} — yenile`}
                          disabled={!online || busy || pending.has(entry.id)}
                          onClick={() => refreshOne(entry.id)}
                        >
                          <RefreshCw size={14} className={pending.has(entry.id) ? "animate-spin" : undefined} />
                        </IconButton>
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
        hint="Eşikler backend özetinden gelir: devre kesici açık, son koşu hata ya da üst üste üç boş koşu."
      >
        {coverage.isPending ? (
          <Spinner label="Kaynak sağlığı yükleniyor…" />
        ) : coverage.isError ? (
          <Empty
            title="Kaynak sağlığı yüklenemedi"
            action={
              <Button size="sm" onClick={() => void coverage.refetch()}>
                Yeniden dene
              </Button>
            }
          >
            Sağlık özeti alınamadı; bu "sorun yok" anlamına gelmez.
          </Empty>
        ) : problems.length === 0 ? (
          <p className="flex items-center gap-2 text-meta text-ok">
            <CheckCircle2 size={14} /> Sorunlu kaynak yok.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {problems.map((row) => {
              const failing = row.circuit_open || row.last_status === "error";
              const reason = row.circuit_open
                ? "devre açık"
                : row.last_status === "error"
                  ? "son koşu hata"
                  : `${row.consecutive_empty} kez boş`;
              return (
                <li
                  key={row.source}
                  className={cx(
                    "flex flex-wrap items-center gap-2 rounded-control border px-3 py-2 text-meta",
                    failing
                      ? "border-danger/40 bg-danger-surface text-danger"
                      : "border-warn/40 bg-warn-surface text-warn",
                  )}
                >
                  <span className="font-medium">{sourceLabel(row.source)}</span>
                  <Chip tone={failing ? "danger" : "warn"}>{reason}</Chip>
                  <span className="text-micro opacity-80">{CLASS_LABELS[row.class] ?? row.class}</span>
                  {row.last_error && (
                    <span className="min-w-0 truncate opacity-90">
                      {`${row.last_error_kind ?? ""} ${row.last_error}`.trim()}
                    </span>
                  )}
                  <span className="ml-auto text-micro opacity-80">
                    {row.last_success_at ? `son başarı ${relativeTime(row.last_success_at)}` : "hiç başarılı olmadı"}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </Section>

      <Section title="Son koşular">
        {runs.isPending ? (
          <Spinner label="Koşular yükleniyor…" />
        ) : runs.isError ? (
          <Empty
            title="Koşu geçmişi yüklenemedi"
            action={
              <Button size="sm" onClick={() => void runs.refetch()}>
                Yeniden dene
              </Button>
            }
          >
            Son koşular alınamadı.
          </Empty>
        ) : (runs.data ?? []).length === 0 ? (
          <Empty>Henüz kaynak koşusu kaydı yok.</Empty>
        ) : (
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
        )}
      </Section>

      <Section
        title="Kapsam matrisi"
        hint="Hangi kurumu takip ediyoruz, hangisi eksik? Resmî kaynak merkezî kayıttır; kurum siteleri erken sinyal verir."
      >
        {coverage.isPending ? (
          <Spinner label="Kapsam matrisi yükleniyor…" />
        ) : coverage.isError ? (
          <Empty
            title="Kapsam matrisi yüklenemedi"
            action={
              <Button size="sm" onClick={() => void coverage.refetch()}>
                Yeniden dene
              </Button>
            }
          >
            Kaynak kapsamı alınamadı.
          </Empty>
        ) : (coverage.data ?? []).length === 0 ? (
          <Empty>Kapsam verisi yok.</Empty>
        ) : (
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
        )}
      </Section>

      <Section
        title="Disk önbelleği"
        hint="Kaynak yanıtları sınırlı bir bütçeyle saklanır; temizlik yalnızca disk önbelleğine dokunur, PostgreSQL kayıtlarına asla."
      >
        {cache.isPending ? (
          <p className="text-meta text-muted">Önbellek ölçülüyor…</p>
        ) : cache.isError ? (
          <Empty
            title="Önbellek ölçülemedi"
            action={
              <Button size="sm" onClick={() => void cache.refetch()}>
                Yeniden dene
              </Button>
            }
          >
            Disk önbelleği durumu alınamadı.
          </Empty>
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
              <Button
                disabled={!online || pruneCache.isPending}
                onClick={() => pruneCache.mutate()}
                title="Önbelleği bütçeye indir (TTL + LRU)"
              >
                <RefreshCw size={13} /> Bütçeye indir (TTL + LRU)
              </Button>
              <Button
                variant="danger"
                disabled={!online || clearCache.isPending}
                onClick={() => void confirmClearCache()}
                title="Önbelleği temizle"
              >
                Önbelleği temizle
              </Button>
              <span className="text-meta text-muted">Önbellek modu: {cache.data?.mode ?? "off"}</span>
              {!online && <span className="text-meta text-warn">Çevrimdışı: önbellek işlemleri kapalı.</span>}
            </div>
          </>
        )}
      </Section>
    </div>
  );
}
