import { invalidateAfter } from "@/core/invalidation";
import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, Check, Loader2, RefreshCw, Search } from "lucide-react";
import { api } from "@/core/api";
import {Button, Checkbox, Chip, Empty, Input, Metric, MetricStrip, PageFrame, PageHeader, RowList, Section, Toolbar, cx, relativeTime, useToast} from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { useHashRoute } from "@/app/router";
import type {
  SourceHealth, SourceRefreshResult, SourceSyncBatch, SourceSyncStatus,
} from "@/core/types";
import {useOnline} from "@/lib/hooks";
import { sourceLabel } from "@/core/labels";
import {
  sourceSyncApiPath,
  sourceSyncHistoryApiPath,
  sourceSyncHistoryQueryKey,
  sourceSyncQueryKey,
  SyncProgress,
  type SourceSyncScope,
} from "./SyncProgress";

type Catalog = { id: string; interval_minutes: number; kind: string };
const KIND_LABELS: Record<string, string> = { job: "İş ilanı", announcement: "Duyuru" };

/** Kosum durumu -> rozet tonu. "new" = hic calismamis. */
const STATUS_TONE: Record<string, "neutral" | "accent" | "ok" | "warn" | "danger"> = {
  ok: "ok", empty: "warn", error: "danger", running: "accent", queued: "neutral", new: "neutral",
};
const STATUS_LABEL: Record<string, string> = {
  ok: "sağlıklı", empty: "boş döndü", error: "hata", running: "çekiliyor", queued: "sırada", new: "hiç çalışmadı",
};

export function SourceHealthPage() {
  const route = useHashRoute();
  const scope: SourceSyncScope = route.params.get("scope") === "media" ? "media" : "opportunity";
  const online = useOnline();
  const toast = useToast();
  const [kind, setKind] = useState("");
  const [search, setSearch] = useState("");
  const [picked, setPicked] = useState<Set<string>>(new Set());

  const { data: catalog = [] } = useQuery({
    queryKey: ["source-catalog"],
    queryFn: () => api.get<Catalog[]>("/sources/catalog"),
  });
  const { data: runs = [] } = useQuery({
    queryKey: ["source-runs"],
    queryFn: () => api.get<SourceHealth[]>("/sources/runs"),
  });
  // Cekim surerken hizli, bosta seyrek yokla.
  const { data: sync } = useQuery({
    queryKey: sourceSyncQueryKey(scope),
    queryFn: () => api.get<SourceSyncStatus>(sourceSyncApiPath(scope)),
    refetchInterval: (query) => (query.state.data?.running.length ? 2_000 : 15_000),
  });
  const { data: history = [] } = useQuery({
    queryKey: sourceSyncHistoryQueryKey(scope),
    queryFn: () => api.get<SourceSyncBatch[]>(sourceSyncHistoryApiPath(scope)),
    refetchInterval: sync?.active ? 2_000 : 30_000,
  });

  const running = useMemo(
    () => new Set((sync?.running ?? []).map((item) => item.source)),
    [sync],
  );
  const batchSources = useMemo(
    () => new Map((sync?.sources ?? []).map((item) => [item.source, item])),
    [sync],
  );

  /** Kaynak basina son kosum. runs zaten yeniden eskiye sirali. */
  const latest = useMemo(() => {
    const map = new Map<string, SourceHealth>();
    for (const run of runs) if (!map.has(run.source)) map.set(run.source, run);
    return map;
  }, [runs]);

  const statusOf = (id: string) =>
    batchSources.get(id)?.status ?? latest.get(id)?.status ?? "new";

  const refreshOne = useMutation({
    mutationFn: (id: string) => api.post(`/sources/${encodeURIComponent(id)}/refresh`),
    onSuccess: () => invalidateAfter("source.sync"),
  });

  const refreshMany = useMutation({
    mutationFn: (body: { source_ids?: string[]; kind?: string }) =>
      api.post<SourceRefreshResult>("/sources/refresh", body),
    onSuccess: (result) => {
      setPicked(new Set());
      invalidateAfter("source.sync");
      toast.push(
        result.queued
          ? `${result.queued} kaynak kuyruğa alındı`
          : "Seçilen kaynaklar aktif çekimde zaten var",
        { tone: "ok" },
      );
    },
  });

  const visible = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase("tr");
    return catalog.filter((source) => {
      if (kind && source.kind !== kind) return false;
      return !needle || source.id.toLocaleLowerCase("tr").includes(needle);
    });
  }, [catalog, kind, search]);

  const counts = useMemo(() => {
    const tally = { ok: 0, empty: 0, error: 0, new: 0 };
    for (const source of catalog) {
      const status = latest.get(source.id)?.status ?? "new";
      if (status in tally) tally[status as keyof typeof tally] += 1;
    }
    return tally;
  }, [catalog, latest]);

  const allPicked = visible.length > 0 && visible.every((s) => picked.has(s.id));

  function toggle(id: string) {
    setPicked((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setPicked((current) => {
      const next = new Set(current);
      if (allPicked) visible.forEach((s) => next.delete(s.id));
      else visible.forEach((s) => next.add(s.id));
      return next;
    });
  }

  async function syncAll() {
    const ok = await confirmDialog({
      title: "Tüm kaynaklar çekilsin mi?",
      body: `${catalog.length} kaynak arka planda sırayla çekilecek. Bu birkaç dakika sürebilir; bu sırada uygulamayı kullanmaya devam edebilirsin.`,
      confirmLabel: "Tümünü çek",
    });
    if (ok) refreshMany.mutate({});
  }

  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Sistem" title={scope === "media" ? "Medya Kaynak Durumu" : "Kaynak Durumu"} />

      <SyncProgress scope={scope} />

      {scope === "opportunity" && <>
      {/* ── Özet ── */}
      <MetricStrip className="grid-cols-2 md:grid-cols-4">
        <Metric label="Kaynak" value={catalog.length} hint={`${counts.new} hiç çalışmadı`} />
        <Metric label="Sağlıklı" value={counts.ok} hint="son koşumu başarılı" />
        <Metric label="Boş döndü" value={counts.empty} hint="üst üste 3 → bildirim" />
        <Metric label="Hata" value={counts.error} hint="son koşumda hata" />
      </MetricStrip>

      {/* ── Eylemler ── */}
      <Toolbar>
        <div className="relative min-w-[240px] flex-1">
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
          variant="primary"
          disabled={!online || refreshMany.isPending}
          onClick={syncAll}
        >
          <RefreshCw size={15} className={refreshMany.isPending ? "animate-spin" : undefined} />
          Tümünü çek
        </Button>
      </Toolbar>

      {/* ── Tür süzgeci ── */}
      <div className="flex flex-wrap gap-2">
        {[["", "Tümü", catalog.length] as const,
          ...Object.keys(KIND_LABELS).map((value) =>
            [value, KIND_LABELS[value], catalog.filter((s) => s.kind === value).length] as const)]
          .map(([value, label, count]) => (
            <button
              key={value || "all"}
              type="button"
              onClick={() => setKind(value)}
              aria-pressed={kind === value}
              className={cx(
                "flex h-8 items-center gap-2 rounded-control border px-3 text-meta transition",
                kind === value
                  ? "border-accent bg-accent-surface font-medium text-accent"
                  : "border-subtle bg-surface text-secondary hover:bg-surface-hover hover:text-primary",
              )}
            >
              <span>{label}</span>
              <span className={cx("numeral text-meta", kind === value ? "text-accent" : "text-muted")}>{count}</span>
            </button>
          ))}
      </div>

      {/* ── Seçim şeridi ── */}
      <Section
          title="Kaynaklar"
          hint={running.size > 0 ? `${running.size} kaynak çekiliyor` : `${visible.length} kaynak`}
        >

        <div className="overflow-hidden border-y border-subtle">
          <div className="flex items-center gap-3 border-b border-subtle bg-surface-sunken px-4 py-2.5">
            <Checkbox
              checked={allPicked}
              onChange={toggleAll}
              label={picked.size > 0 ? `${picked.size} seçili` : "Hepsini seç"}
            />
            <span className="flex-1" />
            {picked.size > 0 && (
              <>
                <Button size="sm" onClick={() => setPicked(new Set())}>Seçimi temizle</Button>
                <Button
                  size="sm"
                  variant="primary"
                  disabled={!online || refreshMany.isPending}
                  onClick={() => refreshMany.mutate({ source_ids: [...picked] })}
                >
                  <RefreshCw size={14} /> Seçilenleri çek
                </Button>
              </>
            )}
          </div>

          {visible.length === 0 ? (
            <div className="px-4 py-8">
              <Empty>Bu süzgece uyan kaynak yok.</Empty>
            </div>
          ) : (
            <ul>
              {visible.map((source) => {
                const run = batchSources.get(source.id) ?? latest.get(source.id);
                const status = statusOf(source.id);
                const busy = status === "running";
                return (
                  <li
                    key={source.id}
                    className={cx(
                      "flex items-center gap-3 border-b border-subtle px-4 py-2.5 last:border-b-0",
                      picked.has(source.id) && "bg-accent-surface/40",
                    )}
                  >
                    <Checkbox
                      checked={picked.has(source.id)}
                      onChange={() => toggle(source.id)}
                      label={<span className="sr-only">{source.id} seç</span>}
                      className="shrink-0"
                    />

                    <div className="min-w-0 flex-1">
                      <p className="truncate text-body text-primary">{sourceLabel(source.id)}</p>
                      <p className="truncate text-meta text-muted">
                        {KIND_LABELS[source.kind] ?? source.kind}
                        {" · her "}{Math.round(source.interval_minutes / 60)} saatte
                        {" · "}
                        {run?.started_at ? relativeTime(run.started_at) : "hiç çalışmadı"}
                      </p>
                      {run?.error && (
                        <p className="mt-0.5 flex items-center gap-1.5 truncate text-meta text-danger">
                          <AlertTriangle size={12} className="shrink-0" />
                          {run.error}
                        </p>
                      )}
                    </div>

                    <span className="w-12 shrink-0 text-right">
                      {run && run.items_found > 0 && (
                        <span className="numeral text-heading text-secondary">+{run.items_found}</span>
                      )}
                    </span>

                    <span className="w-[92px] shrink-0 text-right">
                      <Chip tone={STATUS_TONE[status] ?? "neutral"}>
                        {STATUS_LABEL[status] ?? status}
                      </Chip>
                    </span>

                    <button
                      type="button"
                      disabled={!online || busy || refreshOne.isPending}
                      onClick={() => refreshOne.mutate(source.id)}
                      title={busy ? "Şu an çekiliyor" : "Bu kaynağı şimdi çek"}
                      aria-label={`${source.id} kaynağını çek`}
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control border border-subtle text-muted transition hover:bg-surface-hover hover:text-primary disabled:opacity-40"
                    >
                      {busy
                        ? <Loader2 size={14} className="animate-spin text-accent" />
                        : status === "ok" && run?.items_found === 0
                          ? <Check size={14} />
                          : <RefreshCw size={14} />}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <p className="mt-3 text-meta text-muted">
          Otomatik turlar en bayat dört kaynağı çeker; tam tarama bilinçli bir eylemdir.
          Her koşu <code className="font-mono text-micro">source_run</code>’a yazılır — üst üste üç boş koşu bildirim üretir.
        </p>
      </Section>
      </>}

      <Section title="Son senkronizasyonlar" hint={`${history.length} koşum`}>
        {history.length === 0 ? (
          <Empty>Henüz tamamlanmış manuel çekim yok.</Empty>
        ) : (
          <RowList>
            {history.map((batch) => {
              const duration = batch.started_at && batch.finished_at
                ? Math.max(0, Math.round((new Date(batch.finished_at).getTime() - new Date(batch.started_at).getTime()) / 1000))
                : null;
              return (
                <div key={batch.id} className="flex flex-wrap items-center gap-3 border-b border-subtle px-4 py-3 last:border-b-0">
                  <span className="min-w-36 text-body text-primary">{relativeTime(batch.created_at)}</span>
                  <Chip tone={batch.error_sources ? "danger" : "ok"}>
                    {batch.error_sources ? "hatalarla tamamlandı" : "tamamlandı"}
                  </Chip>
                  <span className="text-meta text-secondary">{batch.total_sources} kaynak</span>
                  <span className="text-meta text-secondary">+{batch.items_found} kayıt</span>
                  {batch.error_sources > 0 && (
                    <span className="text-meta text-danger">{batch.error_sources} hata</span>
                  )}
                  {duration !== null && <span className="ml-auto text-meta text-muted">{duration} sn</span>}
                </div>
              );
            })}
          </RowList>
        )}
      </Section>
    </PageFrame>
  );
}
