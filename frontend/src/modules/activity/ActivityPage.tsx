import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, BookOpen, Briefcase, ChevronDown, ChevronsUpDown, Flame, ListChecks, Timer } from "lucide-react";
import { api, qs } from "@/core/api";
import { entityRoute, typeLabel } from "@/core/entityRegistry";
import { POMODORO_STATS_QUERY_KEY } from "@/modules/pomodoro/queries";
import {
  Button,
  Empty,
  Input,
  Metric,
  MetricStrip,
  PageFrame,
  Section,
  SectionHeader,
  SkeletonRows,
  Tabs,
  cx,
} from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { useDebounced } from "@/lib/hooks";
import { formatTrDate, formatTrDateTime, localDateKey } from "@/lib/date";
import type { ActivityEvent, PomodoroStats } from "@/core/types";
import { describe, verbIcon } from "@/core/verbs";
import { Heatmap } from "./Heatmap";
import { RANGES, type RangeId as RangeIdSource } from "./ranges";
import { MonthlyBars, monthTotal, useRhythmSummary } from "./RhythmWidget";

function dayLabel(iso: string): string {
  return formatTrDate(iso, { weekday: "long", day: "numeric", month: "long" });
}

/** Ilgili kaydin adresi: tip->rota kayit defterinden gelir (kural 13). */
function entityLink(event: ActivityEvent): string | null {
  if (!event.entity_id || !event.entity_type) return null;
  const route = entityRoute(event.entity_type, event.entity_id);
  return route === "#/" ? null : `#${route.replace(/^#/, "")}`;
}

// Zaman araligi secenekleri ortak kaynaktan gelir (Isı Haritası sayfasi ile ayni).
type RangeId = RangeIdSource;

/**
 * Akis filtreleri: "bu kayit hangi alandan geldi?"
 *
 * Hepsi SUNUCUDA suzulur (backend/app/core/events.py ACTIVITY_FILTERS);
 * "Uyarılar" da oyle -- istemci yalnizca cekilen sayfayi suzerse pencere
 * disindaki uyari hic gorunmez.
 */
const FEED_FILTERS = [
  { id: "all", label: "Tümü" },
  { id: "tasks", label: "Görevler" },
  { id: "focus", label: "Odak" },
  { id: "learning", label: "Öğrenme" },
  // "Okuma" yerine Kütüphane: kapsam tam olarak Kütüphane alanidir
  // (yer imi + RSS + medya + not) ve kullanici bu adi sidebar'da goruyor.
  { id: "reading", label: "Kütüphane" },
  { id: "career", label: "Kariyer" },
  { id: "system", label: "Sistem" },
  { id: "alerts", label: "Uyarılar" },
] as const;
type FeedFilter = (typeof FEED_FILTERS)[number]["id"];

const PAGE_SIZE = 50;
const MAX_LIMIT = 500;

/**
 * Etkinlik: (1) Ritim -- seri, bugunun sayilari ve emek haritasi,
 * (2) Trend -- aylik ozet (ikincil), (3) Hareket akisi -- alan filtreleri,
 * arama ve gun gruplari. Kaynak sagligi BURADA DEGIL: sahibi Ayarlar >
 * Durum & Kaynaklar.
 */
export function ActivityPage() {
  const [range, setRange] = useState<RangeId>("1y");
  const [filter, setFilter] = useState<FeedFilter>("all");
  const [search, setSearch] = useState("");
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [openDays, setOpenDays] = useState<Set<string>>(new Set());

  const query = useDebounced(search, 300);

  const { summary, monthly } = useRhythmSummary();
  const { data: pomodoro } = useQuery({
    queryKey: POMODORO_STATS_QUERY_KEY,
    queryFn: () => api.get<PomodoroStats>("/pomodoro/stats?range=day"),
  });
  const { data = [], isLoading } = useQuery({
    queryKey: ["activity", "feed", filter, query, limit],
    queryFn: () => api.get<ActivityEvent[]>(`/activity${qs({ limit, filter, q: query || undefined })}`),
  });
  const dayEntries = useMemo(() => {
    const entries = new Map<string, { key: string; label: string; events: ActivityEvent[] }>();
    for (const event of data.filter(
      (item) =>
        filter !== "all" ||
        (item.verb !== "review.completed" &&
          !item.verb.startsWith("source_sync.") &&
          !item.verb.startsWith("system.") &&
          !item.verb.startsWith("backup.") &&
          !item.verb.startsWith("media.sync_") &&
          !item.verb.startsWith("media.artwork_") &&
          !item.verb.startsWith("calendar.synced") &&
          !item.verb.startsWith("document.synced")),
    )) {
      // Gruplama app gunune gore -- backend heatmap'i ile ayni gun.
      const key = localDateKey(new Date(event.occurred_at));
      const entry = entries.get(key) ?? { key, label: dayLabel(event.occurred_at), events: [] };
      entry.events.push(event);
      entries.set(key, entry);
    }
    return [...entries.values()];
  }, [data]);
  const dayKeys = useMemo(() => dayEntries.map(({ key }) => key), [dayEntries]);
  const allDaysOpen = dayKeys.length > 0 && dayKeys.every((day) => openDays.has(day));
  const canLoadMore = data.length === limit && limit < MAX_LIMIT;

  const counters = summary?.counters ?? {};
  const readToday = (counters.rss_read?.today ?? 0) + (counters.bookmarks?.today ?? 0);
  const activeRange = RANGES.find((item) => item.id === range) ?? RANGES[2];

  useEffect(() => {
    setOpenDays((current) => {
      const visibleDays = new Set(dayKeys);
      const next = new Set([...current].filter((day) => visibleDays.has(day)));
      if (dayKeys.length > 0 && !dayKeys.some((day) => next.has(day))) {
        next.add(dayKeys[0]);
      }
      return next.size === current.size && [...next].every((day) => current.has(day)) ? current : next;
    });
  }, [dayKeys]);

  function setDayOpen(day: string, open: boolean) {
    setOpenDays((current) => {
      const next = new Set(current);
      if (open) next.add(day);
      else next.delete(day);
      return next;
    });
  }

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader eyebrow="Etkinlik" title="Etkinlik & Ritim" />

        <WorkspaceScrollArea className="space-y-4 p-3">
          {/* Katman 1: Ritim -- bugun nerede oldugun ve son bir yilin. */}
          <SectionHeader label="Ritim" />
          <MetricStrip className="grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
            <Metric
              label="Kesintisiz seri"
              value={
                <span className="flex items-center gap-1.5">
                  <Flame size={15} className="text-warn" />
                  {summary?.streak.current ?? 0} gün
                </span>
              }
              hint={`rekor ${summary?.streak.longest ?? 0} gün`}
            />
            <Metric
              label="Bugün odak"
              value={
                <span className="flex items-center gap-1.5">
                  <Timer size={15} className="text-muted" />
                  {pomodoro?.minutes ?? 0} dk
                </span>
              }
              hint={`${pomodoro?.sessions ?? 0} seans${pomodoro?.interrupted ? ` · ${pomodoro.interrupted} kesinti` : ""}`}
            />
            <Metric
              label="Bugün görev"
              value={
                <span className="flex items-center gap-1.5">
                  <ListChecks size={15} className="text-ok" />
                  {counters.todos?.today ?? 0}
                </span>
              }
              hint={`bu hafta ${counters.todos?.week ?? 0}`}
            />
            <Metric
              label="Bugün okunan"
              value={
                <span className="flex items-center gap-1.5">
                  <BookOpen size={15} className="text-muted" />
                  {readToday}
                </span>
              }
              hint={`bu hafta ${(counters.rss_read?.week ?? 0) + (counters.bookmarks?.week ?? 0)}`}
            />
            <Metric
              label="Bugün başvuru"
              value={
                <span className="flex items-center gap-1.5">
                  <Briefcase size={15} className="text-accent" />
                  {summary?.applications.today ?? 0}
                </span>
              }
              hint={`toplam ${summary?.applications.total ?? 0}`}
            />
          </MetricStrip>

          {/* Harita blogu: aralik secici YALNIZ haritayi etkiler, bu yuzden
              haritanin kendi kontrol satirindadir -- sayfa filtresi degildir.
              Kayit/aktif gun sayilari haritanin alt seridinde, secilen
              aralikla tutarli olarak yasar (ikinci bir sorgu yok). */}
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="label-caps text-muted">Harita aralığı</span>
              <Tabs
                value={range}
                onChange={(next) => setRange(next)}
                ariaLabel="Harita aralığı"
                items={RANGES.map((item) => ({ id: item.id, label: item.label }))}
              />
              <a href="#/activity/heatmap" className="ml-auto shrink-0 text-meta text-accent hover:underline">
                Haritayı ayrı aç →
              </a>
            </div>
            <Heatmap days={activeRange.days} />
          </div>

          {/* Katman 2: aylik gelisim -- ikincil; kirilim tooltip'te. */}
          {monthly.length > 0 && (
            <Section title="Trend" hint="aylık özet" bodyClassName="space-y-2 px-3.5 py-3">
              <MonthlyBars points={monthly} />
              <p className="text-meta text-muted">
                Son {monthly.length} ayda {monthly.reduce((sum, point) => sum + monthTotal(point), 0)} hareket
                {monthly.some((point) => point.applications > 0) ? " · başvurular dahil" : ""} · üzerine gelince kırılım
                görünür.
              </p>
            </Section>
          )}

          {/* Ayrıntılı olaylar yalnız isteyince açılır; ritim ana yüzeydir. */}
          <details className="rounded-card border border-subtle bg-surface">
            <summary className="cursor-pointer px-3.5 py-3 text-body font-medium text-secondary">
              Detaylı geçmiş
            </summary>
            <Section
              title="Hareket akışı"
              hint={`${data.length}${canLoadMore ? "+" : ""} hareket · ${dayKeys.length} gün`}
              action={
                <div className="flex items-center gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setOpenDays(new Set(allDaysOpen ? [] : dayKeys))}
                    disabled={dayKeys.length === 0}
                  >
                    <ChevronsUpDown size={13} />
                    {allDaysOpen ? "Tümünü kapat" : "Tümünü aç"}
                  </Button>
                  {limit > PAGE_SIZE && (
                    <Button size="sm" variant="ghost" onClick={() => setLimit(PAGE_SIZE)} title="Akışı ilk sayfaya al">
                      başa al
                    </Button>
                  )}
                </div>
              }
            >
              <div className="flex flex-wrap items-center gap-2">
                <Tabs
                  value={filter}
                  onChange={(next) => setFilter(next)}
                  ariaLabel="Hareket filtresi"
                  items={FEED_FILTERS.map((item) => ({ id: item.id, label: item.label }))}
                />
                <Input
                  value={search}
                  onChange={setSearch}
                  placeholder="Hareketlerde ara…"
                  ariaLabel="Hareketlerde ara"
                  className="h-8 w-full text-meta sm:ml-auto sm:w-56"
                />
              </div>

              <div className="mt-3 space-y-2">
                {isLoading ? (
                  <SkeletonRows rows={6} />
                ) : data.length === 0 ? (
                  <Empty>{query ? "Aramayla eşleşen hareket yok." : "Bu filtrede hareket yok."}</Empty>
                ) : (
                  <>
                    {dayEntries.map(({ key, label, events: dayEvents }) => {
                      const alertCount = dayEvents.filter((event) => event.is_alert).length;
                      const open = openDays.has(key);
                      return (
                        <details
                          key={key}
                          data-activity-day
                          open={open}
                          onToggle={(event) => setDayOpen(key, event.currentTarget.open)}
                          className="overflow-hidden rounded-card border border-subtle bg-surface"
                        >
                          <summary className="flex cursor-pointer list-none items-center gap-3 px-3.5 py-2 marker:content-none">
                            <ChevronDown
                              className={cx("shrink-0 transition-transform", open && "rotate-180")}
                              size={15}
                            />
                            <span className="label-caps truncate text-secondary">{label}</span>
                            <span className="ml-auto shrink-0 text-meta text-muted">{dayEvents.length} hareket</span>
                            {alertCount > 0 && (
                              <span className="flex shrink-0 items-center gap-1.5 text-meta text-warn">
                                <span className="h-1.5 w-1.5 rounded-full bg-warn" aria-hidden />
                                {alertCount} uyarı
                              </span>
                            )}
                            <a
                              href={`#/day?d=${key}`}
                              title={`${label} gününü aç`}
                              aria-label={`${label} gününü aç`}
                              className="shrink-0 text-muted transition hover:text-primary"
                            >
                              <ArrowUpRight size={14} />
                            </a>
                          </summary>
                          <ul className="divide-y divide-subtle border-t border-subtle px-3.5">
                            {dayEvents.map((event) => {
                              const Icon = verbIcon(event.verb);
                              const link = entityLink(event);
                              return (
                                <li key={event.id} className="flex items-start gap-2.5 py-2 text-body">
                                  <Icon
                                    size={14}
                                    className={cx("mt-1 shrink-0", event.is_alert ? "text-warn" : "text-icon")}
                                  />
                                  <span
                                    className={cx("min-w-0 flex-1", event.is_alert ? "text-warn" : "text-secondary")}
                                  >
                                    {describe(event.verb, event.payload)}
                                  </span>
                                  {link && (
                                    <a
                                      href={link}
                                      className="mt-0.5 flex shrink-0 items-center gap-0.5 text-meta text-muted transition hover:text-accent"
                                    >
                                      {typeLabel(event.entity_type ?? "")}
                                      <ArrowUpRight size={12} />
                                    </a>
                                  )}
                                  <span className="numeral mt-0.5 shrink-0 text-meta tabular-nums text-muted">
                                    {formatTrDateTime(event.occurred_at, { hour: "2-digit", minute: "2-digit" })}
                                  </span>
                                </li>
                              );
                            })}
                          </ul>
                        </details>
                      );
                    })}

                    {canLoadMore && (
                      <div className="flex justify-center pt-1">
                        <Button onClick={() => setLimit((current) => Math.min(MAX_LIMIT, current + PAGE_SIZE))}>
                          Daha fazla yükle
                        </Button>
                      </div>
                    )}
                  </>
                )}
              </div>
            </Section>
          </details>
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
