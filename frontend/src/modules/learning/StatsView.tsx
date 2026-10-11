/**
 * Öğrenme istatistikleri (Faz 11).
 *
 * Kaynak: `GET /study/stats?range=week|month|90d|year|all`. Aralık URL'de
 * yasar (`?range=`) ki gorunum paylasilabilir/paylasilan baglantiyla ayni
 * sekilde acilsin.
 *
 * Gorsellestirme YALNIZCA mevcut token + core/ui ile kurulur: harici grafik
 * kutuphanesi yok. Her grafigin yaninda sayilar METIN olarak da durur; cubuk
 * yalnizca orani sezdirir (erisilebilirlik: renk/uzunluk tek basina anlatmaz).
 */
import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import type { components } from "@/generated/api-schema";
import { api, qs } from "@/core/api";
import {
  Button,
  Empty,
  FilterChip,
  Metric,
  MetricStrip,
  RowList,
  SectionHeader,
  SkeletonRows,
  Toolbar,
  cx,
} from "@/core/ui";
import { navigate, useHashRoute } from "@/app/router";

type StudyStats = components["schemas"]["StudyStatsOut"];
type StatsArea = components["schemas"]["StatsAreaOut"];
type StatsTopic = components["schemas"]["StatsTopicOut"];

/** Backend `_RANGES` anahtarlari; ilk deger varsayilan araliktir. */
const RANGES = ["week", "month", "90d", "year", "all"] as const;
type Range = (typeof RANGES)[number];

const RANGE_LABEL: Record<Range, string> = {
  week: "Bu hafta",
  month: "Bu ay",
  "90d": "90 gün",
  year: "Bu yıl",
  all: "Tümü",
};

/** Ayni olcekteki cubuklar icin sayi etiketi. */
const minutesText = (minutes: number): string => `${minutes} dk`;

const durationText = (minutes: number): string => {
  if (minutes < 60) return `${minutes} dk`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} sa` : `${hours} sa ${rest} dk`;
};

/** Cubuk genisligi: en buyuk degere gore yuzde. Deger yoksa cizilmez. */
const barWidth = (value: number, max: number): string => `${max > 0 ? Math.round((value / max) * 100) : 0}%`;

export function StatsView({ onOpenTopic }: { onOpenTopic: (topicId: string) => void }) {
  const route = useHashRoute();
  const requested = route.params.get("range") ?? "";
  const range: Range = (RANGES as readonly string[]).includes(requested) ? (requested as Range) : "week";

  const stats = useQuery({
    queryKey: ["study-stats", range],
    queryFn: () => api.get<StudyStats>(`/study/stats${qs({ range })}`),
  });

  const selectRange = (next: Range) => {
    const params = new URLSearchParams(route.params);
    params.set("view", "stats");
    params.set("range", next);
    navigate(`/learning?${params.toString()}`);
  };

  const chips = (
    <Toolbar className="border-t-0 pt-0">
      {RANGES.map((option) => (
        <FilterChip
          key={option}
          label={RANGE_LABEL[option]}
          active={option === range}
          onClick={() => selectRange(option)}
        />
      ))}
    </Toolbar>
  );

  if (stats.isLoading) {
    return (
      <div className="stack-y-3">
        <p role="status" className="text-meta text-muted">
          İstatistikler yükleniyor…
        </p>
        <SkeletonRows rows={4} />
      </div>
    );
  }

  if (stats.isError) {
    return (
      <div role="alert">
        <Empty
          variant="page"
          title="İstatistikler yüklenemedi"
          action={
            <Button disabled={stats.isFetching} onClick={() => void stats.refetch()}>
              Yeniden dene
            </Button>
          }
        >
          Sunucudan yanıt alamadım: {stats.error.message}
        </Empty>
      </div>
    );
  }

  const data = stats.data;
  if (!data) return chips;

  const byArea: StatsArea[] = data.by_area ?? [];
  const byTopic: StatsTopic[] = data.by_topic ?? [];
  const maxArea = Math.max(0, ...byArea.map((row) => row.minutes));
  const maxTopic = Math.max(0, ...byTopic.map((row) => row.minutes));
  const courses = data.courses ?? { total: 0, done: 0, in_progress: 0 };
  const emptiness =
    data.focus_minutes === 0 &&
    data.focus_sessions === 0 &&
    data.topics_done === 0 &&
    data.topics_started === 0 &&
    data.resources_done === 0 &&
    data.reviews_done === 0 &&
    data.flashcards_reviewed === 0 &&
    data.active_days === 0 &&
    byArea.length === 0 &&
    byTopic.length === 0;

  return (
    <div className="stack-y-5">
      <SectionHeader label="İstatistikler" hint={RANGE_LABEL[range]} />
      {chips}

      {emptiness ? (
        <Empty
          variant="page"
          title="Bu aralıkta veri yok"
          action={<Button onClick={() => navigate("/learning?view=topics")}>Konulara git</Button>}
        >
          Bu aralıkta odak seansı, tamamlanan kaynak ya da tekrar kaydı yok. Aralığı genişletmeyi ya da bir konuda odak
          seansı başlatmayı dene.
        </Empty>
      ) : (
        <>
          <MetricStrip className="grid-cols-2 sm:grid-cols-4">
            <Metric
              label="Odak süresi"
              value={durationText(data.focus_minutes)}
              hint={minutesText(data.focus_minutes)}
            />
            <Metric label="Odak seansı" value={data.focus_sessions} />
            <Metric label="Öğrenilen konu" value={data.topics_done} />
            <Metric label="Tamamlanan kaynak" value={data.resources_done} />
            <Metric label="Tekrar" value={data.reviews_done} hint={`${data.topics_started} konu başladı`} />
            <Metric label="Aktif gün" value={data.active_days} />
            <Metric label="Seri" value={`${data.streak_days} gün`} hint="Kesintisiz çalışma" />
            <Metric label="Kart tekrarı" value={data.flashcards_reviewed} />
          </MetricStrip>

          <section>
            <SectionHeader
              label="Güven değişimi"
              hint="Konu güven puanlarındaki net değişim"
              action={
                <span
                  className={cx(
                    "numeral text-title",
                    data.confidence_delta > 0 ? "text-ok" : data.confidence_delta < 0 ? "text-danger" : "text-muted",
                  )}
                >
                  {data.confidence_delta > 0 ? `+${data.confidence_delta}` : data.confidence_delta}
                </span>
              }
            />
          </section>

          <section>
            <SectionHeader label="Alan bazında süre" hint={`${byArea.length} alan`} />
            {byArea.length === 0 ? (
              <Empty>Bu aralıkta alan bazında odak süresi yok.</Empty>
            ) : (
              <RowList as="ul">
                {byArea.map((row) => (
                  <li key={row.area_id} className="flex items-center gap-3 py-2">
                    <span className="min-w-0 flex-1 truncate text-body text-primary">{row.title}</span>
                    <span
                      aria-hidden
                      className="hidden h-1.5 w-40 overflow-hidden rounded-control bg-surface-sunken sm:block"
                    >
                      <span className="block h-full bg-accent" style={{ width: barWidth(row.minutes, maxArea) }} />
                    </span>
                    <span className="numeral shrink-0 text-meta text-secondary">{minutesText(row.minutes)}</span>
                  </li>
                ))}
              </RowList>
            )}
          </section>

          <section>
            <SectionHeader label="Konu bazında süre" hint="En çok çalışılan 10 konu" />
            {byTopic.length === 0 ? (
              <Empty>Bu aralıkta konu bazında odak süresi yok.</Empty>
            ) : (
              <RowList as="ul">
                {byTopic.map((row) => (
                  <li key={row.topic_id}>
                    <button
                      type="button"
                      onClick={() => onOpenTopic(row.topic_id)}
                      className="flex w-full items-center gap-3 py-2 text-left"
                    >
                      <span className="min-w-0 flex-1 truncate text-body text-primary">{row.title}</span>
                      <span
                        aria-hidden
                        className="hidden h-1.5 w-40 overflow-hidden rounded-control bg-surface-sunken sm:block"
                      >
                        <span className="block h-full bg-accent" style={{ width: barWidth(row.minutes, maxTopic) }} />
                      </span>
                      <span className="numeral shrink-0 text-meta text-secondary">{minutesText(row.minutes)}</span>
                    </button>
                  </li>
                ))}
              </RowList>
            )}
          </section>

          <section>
            <SectionHeader label="Planlanan ve gerçekleşen" hint="Plan blokları ile odak seansları" />
            <MetricStrip className="grid-cols-2">
              <Metric label="Planlanan" value={durationText(data.planned_minutes)} />
              <Metric
                label="Gerçekleşen"
                value={durationText(data.actual_minutes)}
                hint={
                  data.planned_minutes === 0
                    ? "Bu aralıkta planlanmış çalışma yok"
                    : `Planın %${Math.round((data.actual_minutes / data.planned_minutes) * 100)}'i`
                }
              />
            </MetricStrip>
          </section>

          <section>
            <SectionHeader label="Kurs ilerlemesi" hint={`${courses.total} kurs`} />
            <MetricStrip className="grid-cols-3">
              <Metric label="Kurs" value={courses.total} />
              <Metric label="Bitti" value={courses.done} />
              <Metric label="Devam ediyor" value={courses.in_progress} />
            </MetricStrip>
          </section>

          <section>
            <SectionHeader label="Haftalık değerlendirme" hint="Haftanın tümü tek ekranda" />
            <a href="#/review/weekly" className="inline-flex items-center gap-1.5 text-meta text-accent">
              <ExternalLink size={13} /> Değerlendirmeyi aç
            </a>
          </section>
        </>
      )}
    </div>
  );
}
