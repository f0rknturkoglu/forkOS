import { useQuery } from "@tanstack/react-query";
import { navigate, useHashRoute } from "@/app/router";
import { api, qs } from "@/core/api";
import type { components } from "@/generated/api-schema";
import { Button, Empty, FilterChip, PageFrame, RowList, Section, Stat, cx } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { useOnline } from "@/lib/hooks";
import { MediaMetrics } from "./MediaPosterGrid";
import { measureLabel } from "./MediaSessionTransfer";
import {
  Cover,
  KIND_LABELS,
  kindBg,
  mediaCoverUrl,
  mediaProvider,
  providerChip,
  providerLabel,
  statusLabel,
} from "./shared";

type MediaStats = components["schemas"]["MediaStats"];
type RecentConsumption = components["schemas"]["MediaRecentConsumptionOut"];

/**
 * Dashboard'un `recent_consumptions` alani uretilen semada hala eski
 * `MediaConsumptionOut`'a bagli; backend baslik/tur tasiyan
 * `MediaRecentConsumptionOut` dondurur (Faz 10 tek istek kurali).
 */
type MediaDashboard = Omit<components["schemas"]["MediaDashboardOut"], "recent_consumptions"> & {
  recent_consumptions: RecentConsumption[];
};

const RANGES = [
  { value: "week", label: "Bu hafta" },
  { value: "month", label: "Bu ay" },
  { value: "90d", label: "Son 90 gün" },
  { value: "year", label: "Bu yıl" },
  { value: "all", label: "Tüm zamanlar" },
] as const;
type Range = (typeof RANGES)[number]["value"];
const DEFAULT_RANGE: Range = "all";

/** Aralik secimi URL'e yazilir (varsayilan deger parametreyi temizler). */
function setRangeParam(route: { path: string; params: URLSearchParams }, range: Range): void {
  const params = new URLSearchParams(route.params);
  if (range === DEFAULT_RANGE) params.delete("range");
  else params.set("range", range);
  const serialized = params.toString();
  navigate(serialized ? `${route.path}?${serialized}` : route.path, { replace: true });
}

/** Son tuketim eylemleri — ham backend degerleri kullanici diline cevrilir. */
const RECENT_ACTION_LABELS: Record<string, string> = {
  quick: "Hızlı ilerleme",
  set: "Düzeltme",
  finish: "Tamamlama",
  complete_unit: "Bölüm tamamlandı",
  uncomplete_unit: "Geri alındı",
  session: "Seans",
};

/**
 * `by_measure` satirlari. Her olcu KENDI satirinda gosterilir: sayfa + bolum +
 * dakika tek toplama BIRLESTIRILMEZ (anlamsiz bir sayi uretirdi).
 */
const MEASURE_METRIC_LABELS: Record<string, string> = {
  page: "Okunan sayfa",
  chapter: "Okunan bölüm",
  episode: "İzlenen bölüm",
  track: "Dinlenen parça",
  minute: "Dinlenen dakika",
  hour: "Dinlenen saat",
  item: "Oynanan kayıt",
  percent: "Yüzde ilerleme",
};
/** Satir sirasi: bilinen olculer once, tanimadiklarimiz adiyla sona eklenir. */
const MEASURE_ORDER = ["page", "chapter", "episode", "track", "minute", "hour", "item", "percent"];

function measureRows(byMeasure: Record<string, number>): { key: string; label: string; value: number }[] {
  const known = MEASURE_ORDER.filter((key) => byMeasure[key] !== undefined).map((key) => ({
    key,
    label: MEASURE_METRIC_LABELS[key],
    value: byMeasure[key],
  }));
  // Tanimadigimiz olcu anahtari gelirse kaybolmasin; adiyla sona eklenir.
  const extra = Object.keys(byMeasure)
    .filter((key) => MEASURE_METRIC_LABELS[key] === undefined)
    .sort()
    .map((key) => ({ key, label: measureLabel(key), value: byMeasure[key] }));
  return [...known, ...extra];
}

/** Saat + dakika bicimi. 0 da gecerli bir degerdir, "—" yalnizca veri yokken. */
function durationLabel(totalMinutes: number | null | undefined): string {
  if (totalMinutes == null) return "—";
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours === 0) return `${minutes} dk`;
  return minutes === 0 ? `${hours} sa` : `${hours} sa ${minutes} dk`;
}

function formatCount(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

/** "2026-09-04" gun anahtarini "4 Eylül"e cevirir (UTC, gun kaymasi olmadan). */
function dayLabel(key: string): string {
  const [year, month, day] = key.split("-").map(Number);
  if (!year || !month || !day) return key;
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  });
}

/** Yatay oranli bar satiri: etiket + dolgu + sayi. Yuzde genislik, yeni paket yok. */
function BarRow({ label, value, max, colorClass }: { label: string; value: number; max: number; colorClass: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <li className="flex items-center gap-3 py-1">
      <span className="w-28 shrink-0 truncate text-meta text-secondary" title={label}>
        {label}
      </span>
      <span className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-sunken">
        <span className={cx("block h-full rounded-full", colorClass)} style={{ width: `${pct}%` }} />
      </span>
      <span className="numeral w-12 shrink-0 text-right text-meta text-primary">{formatCount(value)}</span>
    </li>
  );
}

/** Puan dagilimi: 1-10 kompakt CSS histogram (bar yuksekligi yuzde). */
function ScoreHistogram({ distribution }: { distribution: Record<string, number> }) {
  const counts = Array.from({ length: 10 }, (_, index) => distribution[String(index + 1)] ?? 0);
  const max = Math.max(...counts, 1);
  const summary = counts.map((count, index) => `${index + 1} puan ${count}`).join(" · ");
  return (
    <div>
      <p className="mb-2 text-meta text-secondary">{summary}</p>
      <ul role="img" aria-label={`Puan dağılımı: ${summary}`} className="flex h-28 items-end gap-1.5">
        {counts.map((count, index) => (
          <li key={index} className="flex h-full min-w-0 flex-1 flex-col items-center gap-1">
            <span className="numeral text-micro text-muted">{count}</span>
            <span className="flex min-h-0 w-full flex-1 items-end">
              <span
                className={cx("w-full rounded-t bg-accent", count === 0 && "opacity-20")}
                style={{ height: `${Math.max(Math.round((count / max) * 100), 2)}%` }}
              />
            </span>
            <span className="text-micro text-muted">{index + 1}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Donusum hunisi: Planlandi -> Baslandi -> Tamamlandi (sirali bar + sayilar). */
function ConversionFunnel({ conversion }: { conversion: { planned: number; started: number; completed: number } }) {
  const steps = [
    { key: "planned", label: "Planlandı", value: conversion.planned, colorClass: "bg-muted" },
    { key: "started", label: "Başlandı", value: conversion.started, colorClass: "bg-accent" },
    { key: "completed", label: "Tamamlandı", value: conversion.completed, colorClass: "bg-ok" },
  ];
  const max = Math.max(...steps.map((step) => step.value), 1);
  const summary = steps.map((step) => `${step.label} ${step.value}`).join(" · ");
  return (
    <div>
      <p className="mb-2 text-meta text-secondary">{summary}</p>
      <ul role="img" aria-label={`Dönüşüm: ${summary}`}>
        {steps.map((step) => (
          <BarRow key={step.key} label={step.label} value={step.value} max={max} colorClass={step.colorClass} />
        ))}
      </ul>
    </div>
  );
}

/** Tur dagilimi: siralanmis bar listesi + erisilebilir metinsel ozet. */
function KindDistribution({ byKind }: { byKind: Record<string, number> }) {
  const rows = Object.entries(byKind)
    .map(([kind, count]) => ({ kind, count }))
    .sort(
      (a, b) => b.count - a.count || (KIND_LABELS[a.kind] ?? a.kind).localeCompare(KIND_LABELS[b.kind] ?? b.kind, "tr"),
    );
  const max = Math.max(...rows.map((row) => row.count), 1);
  const summary = rows.map((row) => `${KIND_LABELS[row.kind] ?? row.kind} ${row.count}`).join(" · ");
  return (
    <div>
      <p className="mb-2 text-meta text-secondary">{summary}</p>
      <ul role="img" aria-label={`Tür dağılımı: ${summary}`}>
        {rows.map((row) => (
          <BarRow
            key={row.kind}
            label={KIND_LABELS[row.kind] ?? row.kind}
            value={row.count}
            max={max}
            colorClass={kindBg(row.kind)}
          />
        ))}
      </ul>
    </div>
  );
}

export function MediaStatsPage() {
  const online = useOnline();
  const route = useHashRoute();
  const rawRange = route.params.get("range");
  // `?range=` URL'de tutulur; gecersiz ya da eksik deger "tum zamanlar" sayilir.
  const range: Range = RANGES.some((option) => option.value === rawRange) ? (rawRange as Range) : DEFAULT_RANGE;

  // TEK istek: ozet + devam edenler + yaklasanlar + son tuketimler (Faz 10).
  // `/media/stats` ve kaldirilan `/media/consumptions/recent` AYRICA cagrilmaz.
  const {
    data: dashboard,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["media-dashboard", range],
    queryFn: () => api.get<MediaDashboard>(`/media/dashboard${qs({ range, recent_limit: 20 })}`),
  });

  const stats: MediaStats | undefined = dashboard?.stats;
  const byMeasure = measureRows(stats?.by_measure ?? {});
  const scoreDistribution = stats?.score_distribution ?? {};
  const scoreTotal = Object.values(scoreDistribution).reduce((sum, count) => sum + count, 0);

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader eyebrow="Medya" title="İstatistikler" hint="Kütüphane ritmi" />
        <WorkspaceScrollArea className="space-y-4 p-3">
          <div role="group" aria-label="Zaman aralığı" className="flex flex-wrap gap-2">
            {RANGES.map((option) => (
              <FilterChip
                key={option.value}
                label={option.label}
                active={range === option.value}
                onClick={() => setRangeParam(route, option.value)}
              />
            ))}
          </div>

          {isLoading ? (
            <p role="status" className="text-meta text-muted">
              Medya özeti yükleniyor…
            </p>
          ) : isError ? (
            <div role="alert">
              <Empty
                variant="page"
                action={
                  <Button
                    size="sm"
                    disabled={isFetching}
                    onClick={() => {
                      void refetch();
                    }}
                  >
                    Yeniden dene
                  </Button>
                }
              >
                Medya özeti yüklenemedi: {error.message}
              </Empty>
            </div>
          ) : dashboard && stats ? (
            <>
              <div className="space-y-3">
                <MediaMetrics stats={stats} />
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <Stat label="Toplam süre" value={durationLabel(stats.total_duration_min)} />
                  <Stat label="Odak ile geçen medya süresi" value={durationLabel(stats.pomodoro_minutes)} />
                  <Stat
                    label="Ortalama puan"
                    value={stats.average_score == null ? "—" : `${stats.average_score.toFixed(1)} / 10`}
                    hint={`${stats.scored_count} kayıt puanlandı`}
                  />
                  <Stat label="Aralıkta tamamlanan" value={stats.completed_in_range} />
                </div>
              </div>

              <Section title="Tür dağılımı">
                {Object.keys(stats.by_kind).length === 0 ? (
                  <Empty>Kayıt yok.</Empty>
                ) : (
                  <KindDistribution byKind={stats.by_kind} />
                )}
              </Section>

              <Section title="Ölçü bazlı tüketim">
                {byMeasure.length === 0 ? (
                  <Empty>Bu aralıkta ilerleme kaydı yok.</Empty>
                ) : (
                  <ul className="space-y-1">
                    {byMeasure.map((row) => (
                      <li key={row.key} className="flex items-center justify-between gap-3 py-1">
                        <span className="text-body text-secondary">{row.label}</span>
                        <span className="numeral text-body text-primary">{formatCount(row.value)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </Section>

              <Section title="Dönüşüm">
                <ConversionFunnel conversion={stats.conversion ?? { planned: 0, started: 0, completed: 0 }} />
              </Section>

              <Section title="Puan dağılımı">
                {scoreTotal === 0 ? (
                  <Empty>Bu aralıkta puanlanan kayıt yok.</Empty>
                ) : (
                  <ScoreHistogram distribution={scoreDistribution} />
                )}
              </Section>

              <Section title="Medya ritmi">
                <ul className="space-y-1 text-body text-secondary">
                  <li>Bu aralıkta {stats.active_days} gün medya tükettin.</li>
                  {stats.busiest_day && (
                    <li>
                      En aktif gün: {dayLabel(stats.busiest_day.day)} · {stats.busiest_day.count} kayıt
                    </li>
                  )}
                </ul>
              </Section>

              <Section title="Devam edenler">
                {dashboard.continue_items.length === 0 ? (
                  <Empty>Devam eden kayıt yok. Kütüphaneden bir kaydı açıp ilerledikçe burada görünür.</Empty>
                ) : (
                  <RowList as="ul">
                    {dashboard.continue_items.map((item) => (
                      <li key={item.id} className="flex flex-wrap items-center gap-3 py-2">
                        <Cover url={mediaCoverUrl(item)} title={item.title} size="h-12 w-9" />
                        <div className="min-w-0 flex-1">
                          <a
                            href={`#/media/${encodeURIComponent(item.id)}`}
                            aria-label={`${item.title} detayını aç`}
                            className="block truncate text-body font-medium text-primary hover:text-accent hover:underline"
                          >
                            {item.title}
                          </a>
                          <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-meta text-muted">
                            <span>{statusLabel(item.kind, item.status)}</span>
                            {mediaProvider(item) && (
                              <span className={cx("rounded border px-1.5 py-px", providerChip(mediaProvider(item)))}>
                                {providerLabel(mediaProvider(item))}
                              </span>
                            )}
                          </p>
                        </div>
                        {item.progress != null && (
                          <span className="shrink-0 tabular-nums text-meta text-secondary">
                            {item.progress}
                            {item.total != null ? ` / ${item.total}` : ""}
                          </span>
                        )}
                      </li>
                    ))}
                  </RowList>
                )}
              </Section>

              <Section title="Yaklaşan">
                {dashboard.upcoming.length === 0 ? (
                  <Empty>Yaklaşan içerik yok. Takip edilen bir kaydın yayın takvimi burada görünür.</Empty>
                ) : (
                  <RowList as="ul">
                    {dashboard.upcoming.map((unit) => (
                      <li key={unit.id} className="flex flex-wrap items-center gap-3 py-2">
                        <Cover url={unit.cover_url ?? null} title={unit.title} size="h-12 w-9" />
                        <div className="min-w-0 flex-1">
                          <a
                            href={`#/media/${encodeURIComponent(unit.media_id)}`}
                            aria-label={`${unit.title} kaydını aç`}
                            className="block truncate text-body font-medium text-primary hover:text-accent hover:underline"
                          >
                            {unit.number != null ? `${unit.number}. ` : ""}
                            {unit.title}
                          </a>
                          {unit.release_at && (
                            <p className="mt-0.5 text-meta text-muted">
                              {new Date(unit.release_at).toLocaleDateString("tr-TR", {
                                day: "numeric",
                                month: "long",
                              })}
                              {unit.duration_min != null ? ` · ${unit.duration_min} dk` : ""}
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                  </RowList>
                )}
              </Section>

              <Section title="Son tüketimler">
                {dashboard.recent_consumptions.length === 0 ? (
                  <Empty>Henüz tüketim kaydı yok.</Empty>
                ) : (
                  <RowList as="ul">
                    {dashboard.recent_consumptions.map((entry) => (
                      <li key={entry.id} className="flex flex-wrap items-center gap-3 py-2">
                        <div className="min-w-0 flex-1">
                          <a
                            href={`#/media/${encodeURIComponent(entry.media_id)}`}
                            aria-label={`${entry.title} detayını aç`}
                            className="block truncate text-body font-medium text-primary hover:text-accent hover:underline"
                          >
                            {entry.title}
                          </a>
                          <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-meta text-muted">
                            <span className="rounded border border-subtle px-1.5 py-px">
                              {KIND_LABELS[entry.kind] ?? entry.kind}
                            </span>
                            <span>{RECENT_ACTION_LABELS[entry.action] ?? entry.action}</span>
                            {entry.amount != null && (
                              <span>
                                {formatCount(entry.amount)} {measureLabel(entry.measure ?? null)}
                              </span>
                            )}
                          </p>
                        </div>
                        <time dateTime={entry.occurred_at} className="shrink-0 text-meta text-muted">
                          {new Date(entry.occurred_at).toLocaleString("tr-TR", {
                            day: "numeric",
                            month: "short",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </time>
                      </li>
                    ))}
                  </RowList>
                )}
              </Section>
            </>
          ) : null}

          {!online && <p className="text-meta text-muted">Çevrimdışısın — özet salt okunur.</p>}
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
