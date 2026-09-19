import { useEffect, useMemo, useState } from "react";
import { useSourceHealth } from "@/core/runtimeQueries";
import { POMODORO_STATS_QUERY_KEY } from "@/modules/pomodoro/queries";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  BookOpen,
  Briefcase,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  Flame,
  Timer,
} from "lucide-react";
import { api, qs } from "@/core/api";
import { SourceHealthAccordion } from "@/core/SourceHealthAccordion";
import {
  Button,
  Chip,
  Empty,
  Input,
  Metric,
  MetricStrip,
  PageFrame,
  Section,
  SkeletonRows,
  Tabs,
  cx,
  relativeTime,
} from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { useDebounced } from "@/lib/hooks";
import { formatTrDate, localDateKey } from "@/lib/date";
import { typeLabel } from "@/core/entityRegistry";
import type { ActivityEvent, Heatmap as HeatmapData, PomodoroStats, SourceHealth } from "@/core/types";
import { ALERT_VERBS, describe } from "@/core/verbs";
import { Heatmap } from "./Heatmap";
import { MonthlyBars, monthTotal, useRhythmSummary } from "./RhythmWidget";

/** Geçmiş değerlendirmeler -- GET /reviews ucu. Etiket döneme gore. */
interface ReviewOut {
  id: string;
  kind: "daily" | "weekly";
  period_start: string;
  period_end: string;
  note: string | null;
}

function reviewLabel(start: string, end: string): string {
  const s = new Date(start + "T00:00:00");
  const e = new Date(end + "T00:00:00");
  const month = (d: Date) => formatTrDate(d, { day: "numeric", month: "short" });
  if (s.toDateString() === e.toDateString()) return month(s);
  return `${month(s)} – ${month(e)}`;
}

function dayLabel(iso: string): string {
  return formatTrDate(iso, { weekday: "long", day: "numeric", month: "long" });
}

function isAlert(event: ActivityEvent): boolean {
  return (
    ALERT_VERBS.has(event.verb) || (event.verb === "source_sync.completed" && Number(event.payload.errors ?? 0) > 0)
  );
}

/** Zaman araligi secenekleri: heatmap gun sayisina cevrilir. */
const RANGES = [
  { id: "3m", label: "Son 3 ay", days: 90 },
  { id: "6m", label: "Son 6 ay", days: 180 },
  { id: "1y", label: "Son 1 yıl", days: 365 },
] as const;
type RangeId = (typeof RANGES)[number]["id"];

/**
 * Akis filtreleri. "alerts" sunucuya GITMEZ (uyari listesi arayuzde yasar);
 * digerleri backend kategori filtresidir.
 */
const FEED_FILTERS = [
  { id: "all", label: "Tümü" },
  { id: "alerts", label: "Sadece Uyarılar" },
  { id: "task", label: "Görevler" },
  { id: "focus", label: "Odak" },
  { id: "read", label: "Okuma & Not" },
  { id: "system", label: "Sistem" },
] as const;
type FeedFilter = (typeof FEED_FILTERS)[number]["id"];

/** Sunucu tarafi kategori karsiligi: "Okuma & Not" hem okuma hem not'u kapsar. */
const SERVER_CATEGORY: Record<FeedFilter, string | undefined> = {
  all: undefined,
  alerts: undefined,
  task: "task",
  focus: "focus",
  read: "read",
  system: "system",
};

const PAGE_SIZE = 50;
const MAX_LIMIT = 500;

/**
 * Etkinlik & Ritim: (1) ritim seridi, (2) emek haritasi, (3) aylik trend,
 * (4) canli hareket akisi. Istatistikler modulu buraya birlesti; sayaclar
 * backend'de tek katalogdan gelir, iki ekran ayni gunu ayni sekilde anlatir.
 */
export function ActivityPage() {
  const [range, setRange] = useState<RangeId>("1y");
  const [filter, setFilter] = useState<FeedFilter>("all");
  const [search, setSearch] = useState("");
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [healthOpen, setHealthOpen] = useState(false);
  const [openDays, setOpenDays] = useState<Set<string>>(new Set());
  const query = useDebounced(search, 300);

  const { summary, monthly } = useRhythmSummary();
  const { data: pomodoro } = useQuery({
    queryKey: POMODORO_STATS_QUERY_KEY,
    queryFn: () => api.get<PomodoroStats>("/pomodoro/stats?range=day"),
  });
  const { data: heatmap } = useQuery({
    queryKey: ["activity", "heatmap", 365],
    queryFn: () => api.get<HeatmapData>(`/activity/heatmap${qs({ days: 365 })}`),
    staleTime: 5 * 60_000,
  });
  const { data = [], isLoading } = useQuery({
    queryKey: ["activity", "feed", filter, query, limit],
    queryFn: () =>
      api.get<ActivityEvent[]>(`/activity${qs({ limit, category: SERVER_CATEGORY[filter], q: query || undefined })}`),
  });
  const { data: health = [] } = useSourceHealth();
  const { data: reviews = [] } = useQuery({
    queryKey: ["reviews"],
    queryFn: () => api.get<ReviewOut[]>("/reviews?limit=10"),
  });

  const events = useMemo(() => (filter === "alerts" ? data.filter(isAlert) : data), [data, filter]);
  const dayEntries = useMemo(() => {
    const entries = new Map<string, { key: string; label: string; events: ActivityEvent[] }>();
    for (const event of events) {
      // Gruplama app gunune gore -- backend heatmap'i ile ayni gun.
      const key = localDateKey(new Date(event.occurred_at));
      const entry = entries.get(key) ?? { key, label: dayLabel(event.occurred_at), events: [] };
      entry.events.push(event);
      entries.set(key, entry);
    }
    return [...entries.values()];
  }, [events]);
  const dayKeys = useMemo(() => dayEntries.map(({ key }) => key), [dayEntries]);
  const allDaysOpen = dayKeys.length > 0 && dayKeys.every((day) => openDays.has(day));
  const canLoadMore = data.length === limit && limit < MAX_LIMIT;

  const problems = health.filter((s) => s.status !== "ok");
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
        <WorkspacePaneHeader
          eyebrow="Sistem"
          title="Etkinlik & Ritim"
          hint={`${events.length}${canLoadMore ? "+" : ""} hareket`}
          action={
            <Button size="sm" variant="ghost" onClick={() => setLimit(PAGE_SIZE)} title="Akışı başa al">
              sıfırla
            </Button>
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
        </WorkspacePaneHeader>

        <WorkspaceScrollArea className="space-y-4 p-3">
          <MetricStrip>
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
                  <CheckCircle2 size={15} className="text-ok" />
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

          {problems.length > 0 && (
            <SourceHealthAccordion sources={problems} open={healthOpen} onOpenChange={setHealthOpen} />
          )}

          {/* Katman 2: interaktif emek haritasi. Kare tiklamasi gun sayfasina
              gider (#/day?d=...); orada "bugun" ve "onceki gun" baglantilari var. */}
          <div className="space-y-2">
            <Tabs
              value={range}
              onChange={(next) => setRange(next)}
              ariaLabel="Harita aralığı"
              items={RANGES.map((item) => ({ id: item.id, label: item.label }))}
            />
            <Heatmap days={activeRange.days} />
          </div>

          {/* Katman 3: aylik gelisim. Bar tooltip'i odak/görev/okuma/başvuru kirilimini tasir. */}
          {monthly.length > 0 && (
            <Section
              title="Aylık gelişim"
              hint={monthly.some((point) => point.applications > 0) ? "başvurular dahil" : undefined}
              action={
                heatmap ? (
                  <span className="text-meta text-muted">
                    {heatmap.total} kayıt · {heatmap.active_days} aktif gün
                  </span>
                ) : undefined
              }
            >
              <MonthlyBars points={monthly} />
              <p className="mt-2 text-meta text-muted">
                Toplam {monthly.reduce((sum, point) => sum + monthTotal(point), 0)} hareket · üzerine gelince kırılım
                görünür.
              </p>
            </Section>
          )}

          {reviews.length > 0 && (
            <Section title="Değerlendirmeler">
              <ul className="space-y-1">
                {reviews.map((review) => (
                  <li key={review.id}>
                    <a
                      href={`#/review/${review.kind}`}
                      className="flex items-center gap-2.5 rounded-control border border-subtle bg-surface px-3 py-2 text-body text-secondary transition hover:border-strong hover:text-primary"
                    >
                      <ClipboardCheck size={14} className="shrink-0 text-muted" />
                      <span className="label-caps text-secondary">
                        {review.kind === "weekly" ? "Haftalık" : "Günlük"}
                      </span>
                      <span className="min-w-0 flex-1 truncate text-meta text-muted">
                        {reviewLabel(review.period_start, review.period_end)}
                      </span>
                      {review.note && <span className="truncate text-meta">{review.note}</span>}
                    </a>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {/* Katman 4: canli denetim akisi. */}
          {isLoading ? (
            <SkeletonRows rows={6} />
          ) : events.length === 0 ? (
            <Empty>{query ? "Aramayla eşleşen hareket yok." : "Bu filtrede hareket yok."}</Empty>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setOpenDays(new Set(allDaysOpen ? [] : dayKeys))}
                  disabled={dayKeys.length === 0}
                >
                  {allDaysOpen ? "Tümünü daralt" : "Tümünü genişlet"}
                </Button>
                <span className="text-meta text-muted">{dayKeys.length} gün</span>
              </div>

              {dayEntries.map(({ key, label, events: dayEvents }) => {
                const alertCount = dayEvents.filter(isAlert).length;
                const open = openDays.has(key);
                return (
                  <details
                    key={key}
                    data-activity-day
                    open={open}
                    onToggle={(event) => setDayOpen(key, event.currentTarget.open)}
                    className="overflow-hidden rounded-card border border-subtle bg-surface shadow-card"
                  >
                    <summary className="flex cursor-pointer list-none items-center gap-3 px-3.5 py-2 marker:content-none">
                      <ChevronDown className={cx("transition-transform", open && "rotate-180")} size={15} />
                      <span className="label-caps text-secondary">{label}</span>
                      <span className="ml-auto text-meta text-muted">{dayEvents.length} hareket</span>
                      {alertCount > 0 && <Chip tone="warn">{alertCount} uyarı</Chip>}
                      <a
                        href={`#/day?d=${key}`}
                        title={`${label} gününü aç`}
                        aria-label={`${label} gününü aç`}
                        className="shrink-0 text-muted transition hover:text-primary"
                      >
                        <ArrowUpRight size={14} />
                      </a>
                    </summary>
                    <div className="border-t border-subtle px-3.5 py-3">
                      <ul className="relative ml-1 border-l border-strong">
                        {dayEvents.map((event) => {
                          const alert = isAlert(event);
                          return (
                            <li key={event.id} className="relative min-h-10 py-2 pl-5 text-body">
                              <span className="absolute -left-[5px] top-[15px]" aria-hidden>
                                <span
                                  className={cx(
                                    "block h-2.5 w-2.5 rounded-full ring-[3px] ring-canvas",
                                    alert ? "bg-warn" : "bg-strong",
                                  )}
                                />
                              </span>
                              <div className="min-w-0">
                                <span className={cx(alert ? "text-warn" : "text-secondary")}>
                                  {describe(event.verb, event.payload)}
                                </span>
                                <span className="ml-2 text-meta text-muted">{relativeTime(event.occurred_at)}</span>
                                {event.entity_type && (
                                  <span className="ml-2">
                                    <Chip>{typeLabel(event.entity_type)}</Chip>
                                  </span>
                                )}
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
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
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
