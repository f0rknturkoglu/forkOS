/**
 * Kaynak operasyonları yüzeyi — TEK uygulama, iki çerçeve.
 *
 * Aynı yüzeyi iki yerde görünür: Sistem > Kaynaklar rotası (`/sources`) ve
 * Kariyer > Kaynaklar sekmesi. Fark yalnız başlık/ipucu/vurgudur (`framing`);
 * sorgular, mutasyonlar, satır kuralları ve dürüstlük kuralları ortaktır.
 * İkinci bir kopya YOKTUR — bu dosya silinirse iki yüzey birden susar.
 *
 * Bilgi hiyerarşisi:
 *   başlık (ilerleme + dürüst özet) → özet şerit → İLGİ İSTEYEN (yalnız
 *   gerektiğinde) → İŞLEMLER → KATALOG → AYRINTILAR (koşular, kapsam, disk).
 *
 * Dürüstlük: "veri yok" ≠ "sağlıklı". Katalog/kapsam/koşu/önbellek her biri
 * KENDİ yükleme-hata-boş durumunu taşır (`dataState` + `SectionFallback`);
 * bir uç düştüğünde yalnız o bölüm susar, sayfa "her şey yolunda" demez.
 * Sağlık EŞİĞİ backend'den gelir (`/sources/coverage`); istemci son koşuları
 * dilimleyip karar üretmez.
 */
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, RefreshCw, Search } from "lucide-react";
import { dataState, SectionFallback, type DataState } from "@/core/DataState";
import { confirmDialog } from "@/core/dialog";
import { formatSourceDiagnostics, type SourceDiagnosticsInput, type SourceProblemDiagnostic } from "@/core/diagnostics";
import { sourceLabel } from "@/core/labels";
import {
  circuitView,
  errorKindLabel,
  errorKindTone,
  errorPreview,
  healthSummaryLabel,
  isProblem,
  overallState,
  overallView,
  problemReasons,
  runStateView,
  sourceClassLabel,
  sourceKindLabel,
  SILENT_EMPTY_THRESHOLD,
  type HealthCounts,
} from "@/core/sourceStatus";
import { SyncProgress, useSourceSync, type SourceSyncScope } from "@/core/SyncProgress";
import {
  Button,
  Chip,
  CopyButton,
  Disclosure,
  Empty,
  FilterChip,
  IconButton,
  Input,
  Metric,
  MetricStrip,
  RowList,
  Section,
  Select,
  Toolbar,
  cx,
  relativeTime,
} from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import {
  coverageBySource,
  formatBytes,
  formatSeconds,
  latestRunBySource,
  runningSources,
  sourceRunState,
  syncBySource,
  useSourceCache,
  useSourceCacheClear,
  useSourceCachePrune,
  useSourceCatalog,
  useCareerOpsProviders,
  useSourceCoverage,
  useSourceRefresh,
  useSourceRefreshOne,
  useSourceRuns,
  type CoverageRow,
  type SourceCatalogEntry,
} from "./sourceOps";

/** Çerçeve başına yalnız başlık ve ipucu değişir; veri ve eylemler aynıdır. */
const FRAMING_COPY = {
  system: {
    title: "Kaynak operasyonları",
  },
  career: {
    title: "Kaynak sağlığı",
  },
} as const;

/** Koşu geçmişinde ilk turda gösterilen satır; kalanı katlanır (100 satır dökülmez). */
const RUN_PREVIEW = 10;

/** Kaynak aralığını insan diline çevirir; dakika/saat/gün karışık olabilir. */
function intervalLabel(minutes: number): string {
  if (minutes >= 1440 && minutes % 1440 === 0) return `${minutes / 1440} günde bir`;
  if (minutes >= 60) return `${Math.round(minutes / 60)} saatte bir`;
  return `${minutes} dakikada bir`;
}

/** Tanılama satırı — hepsi kapsam satırının backend alanlarından gelir. */
function problemDiagnostic(row: CoverageRow): SourceProblemDiagnostic {
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

export function SourcesWorkspace({
  framing = "career",
  initialProblemOnly = false,
  focusSource = null,
  syncScope = "opportunity",
}: {
  /** Çerçeveleme: yalnız başlık/ipucu/vurgu değişir. */
  framing?: "system" | "career";
  /** Derin bağlantı (`?filter=problems` / `?problem=1`): sorun süzgeci açık başlar. */
  initialProblemOnly?: boolean;
  /** Derin bağlantı (`?source=<id>`): satır vurgulanır ve görünüme kaydırılır. */
  focusSource?: string | null;
  /** İlerleme şeridinin kapsamı (kariyer = opportunity, medya ayrı sayfada). */
  syncScope?: SourceSyncScope;
}) {
  const online = useOnline();
  const copy = FRAMING_COPY[framing];

  const catalog = useSourceCatalog();
  const careerOps = useCareerOpsProviders();
  const coverage = useSourceCoverage();
  const runs = useSourceRuns();
  const cache = useSourceCache();
  const sync = useSourceSync(syncScope);
  const refresh = useSourceRefresh();
  const refreshOne = useSourceRefreshOne();
  const pruneCache = useSourceCachePrune();
  const clearCache = useSourceCacheClear();

  const [search, setSearch] = useState("");
  const [problemOnly, setProblemOnly] = useState(initialProblemOnly);
  const [classFilter, setClassFilter] = useState("");
  const [kindFilter, setKindFilter] = useState("");
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [allRuns, setAllRuns] = useState(false);
  const [focus, setFocus] = useState<string | null>(focusSource);

  // Derin bağlantı değişince (rota güncellemesi) odak da güncellenir.
  useEffect(() => setFocus(focusSource), [focusSource]);

  const catalogState = dataState(catalog);
  const coverageState = dataState(coverage);
  const runsState = dataState(runs);
  const cacheState = dataState(cache);

  const entries = catalog.data ?? [];
  const coverageRows = coverage.data ?? [];
  const runRows = runs.data ?? [];

  const problemRows = useMemo(
    () => coverageRows.filter(isProblem).sort((left, right) => left.source.localeCompare(right.source)),
    [coverageRows],
  );
  const problemSources = useMemo(() => new Set(problemRows.map((row) => row.source)), [problemRows]);
  const coverageIndex = useMemo(() => coverageBySource(coverageRows), [coverageRows]);
  const latestRuns = useMemo(() => latestRunBySource(runRows), [runRows]);
  const liveBySource = useMemo(() => syncBySource(sync.data), [sync.data]);
  const running = useMemo(() => runningSources(sync.data), [sync.data]);

  const classCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const entry of entries) {
      const key = entry.class ?? "normal";
      counts[key] = (counts[key] ?? 0) + 1;
    }
    return counts;
  }, [entries]);

  const total = entries.length;
  const criticalCount = classCounts.critical ?? 0;
  const optInCount = classCounts.slow_optin ?? 0;
  const regularCount = total - criticalCount - optInCount;
  // "Kritik ve normal" kapsamı: yavaş/isteğe bağlı kaynaklar genel yenilemeye girmez.
  const generalSources = entries.filter((entry) => (entry.class ?? "normal") !== "slow_optin");
  // Süre tahmini katalogdaki `estimated_seconds` toplamıdır (backend alanı).
  const generalSeconds = generalSources.reduce((sum, entry) => sum + (entry.estimated_seconds ?? 0), 0);
  const fullSeconds = entries.reduce((sum, entry) => sum + (entry.estimated_seconds ?? 0), 0);
  const generalHint = `${generalSources.length} kaynak · ~${formatSeconds(generalSeconds)}`;
  const fullHint = `${total} kaynak · ~${formatSeconds(fullSeconds)}`;

  const healthyCount = coverageRows.filter((row) => !isProblem(row) && row.last_status === "ok").length;
  // Özet "bilinmiyor" der; asla sahte "hepsi sağlıklı" demez.
  const summaryUnknown = catalogState !== "ready" || coverageState !== "ready";
  const summary: HealthCounts = {
    total,
    healthy: healthyCount,
    attention: problemRows.length,
    unknown: summaryUnknown,
  };
  const overall = overallView(overallState({ unknown: summaryUnknown, attention: problemRows.length > 0 }));
  const metricValue = (state: DataState, value: number) =>
    state === "ready" ? value : state === "loading" ? "…" : "—";

  const visible = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase("tr");
    return entries
      .filter((entry: SourceCatalogEntry) => {
        // Derin bağlantı hedefi süzgeçlere rağmen görünür kalır: odak kaybolmaz.
        if (entry.id === focus) return true;
        if (problemOnly && !problemSources.has(entry.id)) return false;
        if (classFilter && (entry.class ?? "normal") !== classFilter) return false;
        if (kindFilter && entry.kind !== kindFilter) return false;
        if (!needle) return true;
        return (
          entry.id.toLocaleLowerCase("tr").includes(needle) ||
          sourceLabel(entry.id).toLocaleLowerCase("tr").includes(needle)
        );
      })
      .sort(
        (left, right) =>
          (left.class ?? "normal").localeCompare(right.class ?? "normal") || left.id.localeCompare(right.id),
      );
  }, [entries, search, problemOnly, classFilter, kindFilter, problemSources, focus]);

  // Odak: derin bağlantıyla gelen satır görünüme kaydırılır (kayıt oluşunca da).
  useEffect(() => {
    if (!focus) return;
    const node = document.getElementById(`source-row-${focus}`);
    if (node && typeof node.scrollIntoView === "function") node.scrollIntoView({ block: "center" });
  }, [focus, visible]);

  function refreshSource(id: string) {
    setPending((current) => new Set(current).add(id));
    refreshOne.mutate(id, {
      // Hata da olsa satır düğmesi kilitli kalmasın.
      onSettled: () =>
        setPending((current) => {
          const next = new Set(current);
          next.delete(id);
          return next;
        }),
    });
  }

  async function fullScan() {
    const confirmed = await confirmDialog({
      title: "Tam tarama başlatılsın mı?",
      body: `${total} kaynak sırayla çekilir; yavaş/isteğe bağlı kaynaklar (ör. LinkedIn) DAHİL. Tahmini süre ~${formatSeconds(fullSeconds)}.`,
      confirmLabel: "Tam taramayı başlat",
    });
    if (confirmed) refresh.mutate({ mode: "full" });
  }

  async function confirmClearCache() {
    const confirmed = await confirmDialog({
      title: "Kaynak önbelleği temizlensin mi?",
      body: `${cache.data?.files ?? 0} dosya (${formatBytes(cache.data?.bytes ?? 0)}) silinecek. Bu yalnızca disk önbelleğidir; hiçbir kayıt, not veya başvuru silinmez.`,
      confirmLabel: "Önbelleği temizle",
      tone: "danger",
    });
    if (confirmed) clearCache.mutate();
  }

  const refreshDisabled = !online || refresh.isPending || catalogState !== "ready";

  return (
    <div className="stack-y-4">
      {/* ── Başlık: ilerleme + dürüst toplu durum ── */}
      <div className="stack-y-2">
        <SyncProgress scope={syncScope} compact />
        <div className="flex flex-wrap items-center gap-2">
          <span className="label-caps text-muted">{copy.title}</span>
          <Chip tone={overall.tone}>{overall.label}</Chip>
          <span className="text-meta text-secondary">{healthSummaryLabel(summary)}</span>
        </div>
      </div>

      {/* ── Özet: yükleme sırasında sahte sıfır yok ── */}
      <MetricStrip className="grid-cols-2 md:grid-cols-4">
        <Metric
          label="Kaynak"
          value={metricValue(catalogState, total)}
          hint={
            catalogState === "ready"
              ? `${criticalCount} kritik · ${regularCount} normal · ${optInCount} yavaş`
              : catalogState === "error"
                ? "katalog alınamadı"
                : undefined
          }
        />
        <Metric
          label="Sağlıklı"
          value={metricValue(coverageState, healthyCount)}
          hint={
            coverageState === "ready"
              ? "son koşumu başarılı"
              : coverageState === "error"
                ? "sağlık özeti alınamadı"
                : undefined
          }
        />
        <Metric
          label="İlgi isteyen"
          value={metricValue(coverageState, problemRows.length)}
          hint={coverageState === "ready" ? "devre açık, hata ya da üst üste boş" : undefined}
        />
        <Metric
          label="Çalışıyor"
          value={sync.isError ? "—" : running.size}
          hint={sync.isError ? "durum alınamadı" : running.size > 0 ? "şu an çekiliyor" : undefined}
        />
      </MetricStrip>

      <Section
        title="career-ops sağlayıcıları"
        hint="Sağlayıcı sayısı kaynak sayısı değildir; yalnız yapılandırılmış hedefler taranır."
      >
        {careerOps.isPending ? (
          <p className="text-meta text-muted">Sağlayıcı kayıtları yükleniyor…</p>
        ) : careerOps.isError ? (
          <p role="alert" className="text-meta text-danger">
            Sağlayıcı durumu alınamadı.
          </p>
        ) : (
          <div className="stack-y-2">
            <div className="flex flex-wrap items-center gap-2 text-meta">
              <Chip tone={careerOps.data?.core_ready ? "ok" : "danger"}>
                {careerOps.data?.core_ready ? "çalışıyor" : "çalışmıyor"}
              </Chip>
              <span>
                {careerOps.data?.provider_count ?? 0} sağlayıcı yüklendi (
                {(careerOps.data as { providers_publicly_enumerable?: number })?.providers_publicly_enumerable ?? 22}{" "}
                genel pano · {(careerOps.data as { providers_target_based?: number })?.providers_target_based ?? 62}{" "}
                ATS/şirket hedefli)
              </span>
              <span>{careerOps.data?.configured_boards ?? 0} pano hedefi</span>
              <span>{careerOps.data?.configured_companies ?? 0} şirket hedefi</span>
              <span>{careerOps.data?.plugins_unconfigured ?? 0} eklenti yapılandırılmamış</span>
            </div>
            {careerOps.data?.contribution && (
              <p className="text-meta text-secondary">
                {careerOps.data.contribution.career_ops_seen} fırsatta gözlem ·{" "}
                {careerOps.data.contribution.career_ops_unique} yalnız career-ops ·{" "}
                {careerOps.data.contribution.career_ops_overlap_with_forkjob} forkjob ile ortak ·{" "}
                {careerOps.data.contribution.career_ops_new_canonical} yeni kanonik ·{" "}
                {careerOps.data.contribution.career_ops_existing_strengthened} mevcut kayda katkı
              </p>
            )}
            {careerOps.data?.error && (
              <p role="alert" className="text-meta text-danger">
                {careerOps.data.error}
              </p>
            )}
            {careerOps.data?.core_ready && (
              <p className="text-meta text-muted">
                Node {careerOps.data.node_version} · sabit sürüm {careerOps.data.actual_commit?.slice(0, 7)} · pano ve
                şirket çekimleri tam taramada ayrı kaynaklar olarak görünür.
              </p>
            )}
            {(careerOps.data?.providers?.length ?? 0) > 0 && (
              <Disclosure summary={`Yüklü sağlayıcıları göster (${careerOps.data?.providers?.length})`}>
                <ul className="grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
                  {careerOps.data?.providers?.map((provider) => {
                    const row = provider as {
                      id: string;
                      configured_targets: number;
                      reverse_scan: boolean;
                      category?: string;
                      category_label?: string;
                    };
                    const isBoard = row.category === "A";
                    return (
                      <li
                        key={row.id}
                        className="flex items-center justify-between gap-2 rounded-control border border-line px-2 py-1.5 text-meta"
                      >
                        <span
                          className="min-w-0 truncate"
                          title={`${row.id}${row.category_label ? ` · ${row.category_label}` : ""}`}
                        >
                          {row.id}
                        </span>
                        <Chip
                          tone={row.configured_targets > 0 || isBoard || row.reverse_scan ? "ok" : "neutral"}
                          title={row.category_label}
                        >
                          {row.configured_targets > 0
                            ? `${row.configured_targets} hedef`
                            : isBoard
                              ? "genel pano"
                              : row.reverse_scan
                                ? "ters ATS"
                                : "hedef yok"}
                        </Chip>
                      </li>
                    );
                  })}
                </ul>
              </Disclosure>
            )}
            {(careerOps.data?.plugins?.length ?? 0) > 0 && (
              <p className="text-meta text-muted">
                Anahtar/izin isteyen veya ayrıca etkinleştirilen eklentiler kapalı:{" "}
                {careerOps.data?.plugins?.map((plugin) => plugin.id).join(", ")}.
              </p>
            )}
          </div>
        )}
      </Section>

      {/* ── İLGİ İSTEYEN: yalnız sorun varken panel; yoksa tek sakin satır ── */}
      {coverageState !== "ready" ? (
        <Section title="İlgi isteyen kaynaklar">
          <SectionFallback
            state={coverageState}
            what="Kaynak sağlık özeti"
            onRetry={() => void coverage.refetch()}
            emptyLabel="Kapsam verisi yok."
          />
        </Section>
      ) : problemRows.length === 0 ? (
        <p className="flex items-center gap-2 text-meta text-muted">
          <CheckCircle2 size={14} aria-hidden className="text-ok" /> Şu anda ilgi isteyen kaynak yok.
        </p>
      ) : (
        <Section
          title="İlgi isteyen kaynaklar"
          hint={`Eşik backend'den gelir: devre açık, son koşu hata ya da üst üste ${SILENT_EMPTY_THRESHOLD} boş koşu`}
        >
          <ul className="stack-y-1.5">
            {problemRows.map((row) => {
              const fatal = row.circuit_open || row.last_status === "error";
              return (
                <li
                  key={row.source}
                  className={cx(
                    "flex flex-wrap items-center gap-x-2 gap-y-1.5 rounded-control border px-3 py-2 text-meta",
                    fatal ? "border-danger-border bg-danger-surface" : "border-warn-border bg-warn-surface",
                  )}
                >
                  <span className="font-medium text-primary">{sourceLabel(row.source)}</span>
                  <span className="text-micro text-muted">{row.source}</span>
                  {problemReasons(row).map((reason) => (
                    <Chip key={reason} tone={fatal ? "danger" : "warn"}>
                      {reason}
                    </Chip>
                  ))}
                  {row.last_error && (
                    // Tam (maskelenmiş) metin `title`da kalir; satir kisadir (§66).
                    <span className="min-w-0 flex-1 truncate text-secondary" title={row.last_error}>
                      {errorPreview(row.last_error)}
                    </span>
                  )}
                  <span className="ml-auto shrink-0 text-micro text-muted">
                    {row.last_success_at ? `son başarı ${relativeTime(row.last_success_at)}` : "hiç başarılı olmadı"}
                  </span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setProblemOnly(true);
                      setFocus(row.source);
                    }}
                  >
                    Katalogda göster
                  </Button>
                </li>
              );
            })}
          </ul>
        </Section>
      )}

      {/* ── İŞLEMLER: dürüst etiketli iki tarama + arama + süzgeçler ── */}
      <Section
        title="İşlemler"
        hint='"Yavaş / isteğe bağlı" sınıfı (ör. LinkedIn) genel yenilemeye girmez; tam tarama onları da çeker.'
      >
        <Toolbar className="border-t-0">
          <Button
            variant="primary"
            disabled={refreshDisabled}
            onClick={() => refresh.mutate({ mode: "general" })}
            title={catalogState === "ready" ? generalHint : undefined}
            ariaLabel="Kritik + normal yenile"
          >
            <RefreshCw size={14} aria-hidden /> Kritik + normal yenile
          </Button>
          {catalogState === "ready" && <span className="text-meta text-muted">{generalHint}</span>}
          <Button
            disabled={refreshDisabled}
            onClick={() => void fullScan()}
            title={
              catalogState === "ready"
                ? `Tam tarama — yavaş/isteğe bağlı kaynaklar dahil · ${fullHint}`
                : "Tam tarama — kapsam katalogdan hesaplanır"
            }
            ariaLabel="Tam tarama"
          >
            Tam tarama
          </Button>
          {catalogState === "ready" && <span className="text-meta text-muted">{fullHint}</span>}
        </Toolbar>

        {!online && (
          <p role="status" className="mt-2 text-meta text-warn">
            Çevrimdışı: kaynak çekimi başlatılamaz. Kayıtlı veriler ve önbellek işlemleri çalışmaya devam eder.
          </p>
        )}
        {catalogState !== "ready" && (
          <p className="mt-2 text-meta text-muted">
            {catalogState === "error"
              ? "Kaynak kataloğu alınamadığı için yenileme kapsamı hesaplanamıyor."
              : catalogState === "loading"
                ? "Katalog yükleniyor…"
                : "Katalog boş; yenileme başlatılacak kaynak yok."}
          </p>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <div className="relative min-w-0 flex-[1_1_16rem]">
            <Search
              size={15}
              aria-hidden
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-icon"
            />
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
            count={coverageState === "ready" ? problemRows.length : undefined}
            active={problemOnly}
            icon={<AlertTriangle size={12} aria-hidden />}
            onClick={() => setProblemOnly((value) => !value)}
          />
          <FilterChip
            label="Tüm sınıflar"
            count={catalogState === "ready" ? total : undefined}
            active={classFilter === ""}
            onClick={() => setClassFilter("")}
          />
          {(["critical", "normal", "slow_optin"] as const).map((value) => (
            <FilterChip
              key={value}
              label={sourceClassLabel(value) ?? value}
              count={classCounts[value] ?? 0}
              active={classFilter === value}
              onClick={() => setClassFilter(value)}
            />
          ))}
          <Select value={kindFilter} onChange={setKindFilter} ariaLabel="Kaynak türü">
            <option value="">Tüm türler</option>
            <option value="job">{sourceKindLabel("job")}</option>
            <option value="announcement">{sourceKindLabel("announcement")}</option>
          </Select>
        </div>
      </Section>

      {/* ── KATALOG: durum ve eylemler kaynak başına ── */}
      <Section
        title="Kaynak kataloğu"
        hint={`Durum backend özetinden okunur; "kapalı" bir hata değildir. Kayıt sayısı son koşunun bulduğudur.`}
        action={
          catalogState === "ready" ? (
            <span className="text-meta tabular-nums text-muted">
              {visible.length} / {total}
            </span>
          ) : undefined
        }
      >
        {catalogState !== "ready" ? (
          <SectionFallback
            state={catalogState}
            what="Kaynak kataloğu"
            onRetry={() => void catalog.refetch()}
            emptyLabel="Kaynak kataloğu boş."
          />
        ) : visible.length === 0 ? (
          <Empty title="Eşleşen kaynak yok">
            {problemOnly && coverageState !== "ready"
              ? 'Sağlık özeti alınamadığı için "yalnızca sorunlular" süzgeci uygulanamıyor.'
              : "Arama ya da süzgeç ölçütünü değiştirip yeniden dene."}
          </Empty>
        ) : (
          <ul className="stack-divide-y divide-subtle border-y border-subtle">
            {visible.map((entry) => {
              const row = coverageIndex.get(entry.id);
              const run = latestRuns.get(entry.id);
              const live = liveBySource.get(entry.id);
              const state = runStateView(sourceRunState({ sync: live, coverage: row, run }));
              const circuit = circuitView(row?.circuit_open);
              // Yeniden deneme anı backend'den gelir; yoksa uydurulmaz.
              const retryAt = row?.retry_at ?? entry.retry_at ?? null;
              const kind = errorKindLabel(row?.last_error_kind);
              const problem = isProblem(row);
              // Tanılama paketi YALNIZ sorunlu satırda kurulur: sağlıklı satır
              // ne düğme ne paket üretir.
              const diagnostic: SourceDiagnosticsInput | null =
                problem && row
                  ? {
                      generated_at: new Date().toISOString(),
                      scope: "sources",
                      source_count: catalogState === "ready" ? total : null,
                      problems: [problemDiagnostic(row)],
                      unknown: catalogState === "ready" ? undefined : ["catalog"],
                    }
                  : null;
              const busy = live?.status === "running" || live?.status === "queued";
              const itemsFound = live?.items_found ?? run?.items_found ?? 0;
              // "Son koşu" KAPSAM satırından okunur: koşu geçmişi penceresi
              // kısa olduğu için pencere dışındaki kaynak "hiç çalışmadı"
              // görünemez.
              const lastRunAt = row?.last_run_at ?? run?.started_at ?? null;
              const lastRunLabel = lastRunAt
                ? `son koşu ${relativeTime(lastRunAt)}`
                : coverageState === "ready"
                  ? "hiç çalışmadı"
                  : "son koşu bilinmiyor";
              return (
                <li
                  key={entry.id}
                  id={`source-row-${entry.id}`}
                  className={cx(
                    "flex flex-wrap items-start gap-x-4 gap-y-2 px-3 py-2.5",
                    focus === entry.id && "bg-accent-surface/40",
                  )}
                >
                  <div className="min-w-0 flex-1 basis-full sm:basis-[16rem]">
                    <p className="truncate text-body text-primary">{sourceLabel(entry.id)}</p>
                    <p className="truncate text-micro text-muted">{entry.id}</p>
                    <p className="truncate text-meta text-muted">
                      {[
                        sourceKindLabel(entry.kind),
                        sourceClassLabel(entry.class),
                        intervalLabel(entry.interval_minutes),
                        lastRunLabel,
                        itemsFound > 0 ? `+${itemsFound} yeni kayıt` : null,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                    {row?.last_error && (
                      <p className="truncate text-meta text-danger" title={row.last_error}>
                        {errorPreview(row.last_error)}
                      </p>
                    )}
                    {entry.id === "forkjob_core:linkedin" && (
                      <p className="text-meta text-muted">
                        İsteğe bağlı: Kariyer ayarlarında arama profili, ayrıca proxy dosyası veya açık doğrudan erişim
                        izni gerekir.
                      </p>
                    )}
                  </div>

                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <Chip tone={state.tone}>{state.label}</Chip>
                    {kind && row?.last_error_kind && (
                      <Chip tone={errorKindTone(row.last_error_kind)} title={row.last_error_kind}>
                        {kind}
                      </Chip>
                    )}
                    {circuit && (
                      <Chip tone={circuit.tone}>
                        {retryAt ? `${circuit.label} · ${relativeTime(retryAt)}` : circuit.label}
                      </Chip>
                    )}
                  </div>

                  <div className="ml-auto flex shrink-0 items-center gap-1">
                    {diagnostic && (
                      <CopyButton
                        text={formatSourceDiagnostics(diagnostic)}
                        label="Teşhis"
                        ariaLabel="Bu kaynağın teşhisini kopyala"
                      />
                    )}
                    <IconButton
                      title={`${sourceLabel(entry.id)} — yenile`}
                      disabled={!online || busy || pending.has(entry.id)}
                      onClick={() => refreshSource(entry.id)}
                    >
                      <RefreshCw size={14} aria-hidden className={pending.has(entry.id) ? "animate-spin" : undefined} />
                    </IconButton>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Section>

      {/* ── AYRINTILAR ── */}
      <Section title="Koşu geçmişi" hint={runsState === "ready" ? `${runRows.length} koşum` : undefined}>
        {runsState !== "ready" ? (
          <SectionFallback
            state={runsState}
            what="Koşu geçmişi"
            onRetry={() => void runs.refetch()}
            emptyLabel="Henüz kaynak koşusu kaydı yok."
          />
        ) : (
          <>
            <RowList>
              {(allRuns ? runRows : runRows.slice(0, RUN_PREVIEW)).map((run) => {
                const state = runStateView(run.status);
                return (
                  <div
                    key={`${run.source}:${run.started_at}`}
                    className="flex flex-wrap items-center gap-x-3 gap-y-1 px-1 py-2 text-meta"
                  >
                    <span className="min-w-0 flex-1 truncate text-primary">{sourceLabel(run.source)}</span>
                    <Chip tone={state.tone}>{state.label}</Chip>
                    <span className="tabular-nums text-secondary">
                      {run.started_at ? relativeTime(run.started_at) : "—"}
                    </span>
                    <span className="tabular-nums text-secondary">
                      {run.items_found > 0 ? `+${run.items_found}` : "0"} kayıt
                      {typeof (run as { items_seen?: number }).items_seen === "number" &&
                      (run as { items_seen?: number }).items_seen! > 0 &&
                      (run as { items_seen?: number }).items_seen !== run.items_found
                        ? ` (${(run as { items_seen?: number }).items_seen} görüldü)`
                        : ""}
                    </span>
                    {run.error && (
                      <span className="min-w-0 basis-full truncate text-danger sm:basis-auto" title={run.error}>
                        {run.error}
                      </span>
                    )}
                  </div>
                );
              })}
            </RowList>
            {runRows.length > RUN_PREVIEW && (
              <div className="mt-2">
                <Button size="sm" variant="ghost" ariaExpanded={allRuns} onClick={() => setAllRuns((value) => !value)}>
                  {allRuns ? "Daha az göster" : `Tümünü göster (${runRows.length})`}
                </Button>
              </div>
            )}
          </>
        )}
      </Section>

      <Section title="Kaynak kapsamı" hint="Gelişmiş görünüm: hangi kurumu takip ediyoruz, hangisi eksik?">
        {coverageState !== "ready" ? (
          <SectionFallback
            state={coverageState}
            what="Kapsam matrisi"
            onRetry={() => void coverage.refetch()}
            emptyLabel="Kapsam verisi yok."
          />
        ) : (
          <Disclosure summary={`Kapsam matrisini göster (${coverageRows.length} kaynak)`}>
            <p className="text-meta text-muted">
              Resmî kaynak merkezî kayıttır; kurum siteleri erken sinyal verir. "Üst üste boş" sessiz ölüm
              göstergesidir.
            </p>
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
                  {[...coverageRows]
                    .sort((left, right) => left.source.localeCompare(right.source))
                    .map((row) => {
                      const state = runStateView(row.last_status);
                      const kind = errorKindLabel(row.last_error_kind);
                      return (
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
                            {sourceKindLabel(row.kind) ?? row.kind}
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
                            <span className="flex flex-wrap items-center gap-1.5">
                              <Chip tone={state.tone}>{state.label}</Chip>
                              {kind && row.last_error_kind && (
                                <Chip tone={errorKindTone(row.last_error_kind)}>{kind}</Chip>
                              )}
                              {row.circuit_open && <Chip tone="danger">devre açık</Chip>}
                            </span>
                          </td>
                          <td
                            className="max-w-[16rem] truncate px-2 py-2 text-danger"
                            title={row.last_error ?? undefined}
                          >
                            {row.last_error ?? ""}
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          </Disclosure>
        )}
      </Section>

      <Section
        title="Disk önbelleği"
        hint="Kaynak yanıtları sınırlı bir bütçeyle saklanır; temizlik yalnızca disk önbelleğine dokunur, PostgreSQL kayıtlarına asla."
      >
        {cacheState !== "ready" ? (
          <SectionFallback state={cacheState} what="Disk önbelleği durumu" onRetry={() => void cache.refetch()} />
        ) : (
          <>
            <MetricStrip className="grid-cols-2 md:grid-cols-4">
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
                disabled={pruneCache.isPending}
                onClick={() => pruneCache.mutate()}
                title="Önbelleği bütçeye indir (TTL + LRU)"
                ariaLabel="Bütçeye indir (TTL + LRU)"
              >
                <RefreshCw size={13} aria-hidden /> Bütçeye indir (TTL + LRU)
              </Button>
              <Button
                variant="danger"
                disabled={clearCache.isPending}
                onClick={() => void confirmClearCache()}
                title="Önbelleği temizle"
              >
                Önbelleği temizle
              </Button>
              <span className="text-meta text-muted">Önbellek modu: {cache.data?.mode ?? "off"}</span>
            </div>
            <p className="mt-2 text-meta text-muted">
              Önbellek işlemleri yereldir: internet olmadan da çalışır, çekim ise internet gerektirir.
            </p>
          </>
        )}
      </Section>
    </div>
  );
}
