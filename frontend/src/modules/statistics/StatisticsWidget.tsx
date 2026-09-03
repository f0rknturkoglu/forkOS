import { useQuery } from "@tanstack/react-query";
import { Flame } from "lucide-react";
import { api } from "@/core/api";
import { Section, cx } from "@/core/ui";

/** Istatistik modulu -- heatmap'in hemen altinda duran ozet widget'i.
 *  Yeni tablo yok: backend event toplamlari + opportunity.applied_at uzerinden
 *  salt-okunur sorgular dondurur (KURAL 3 uyumlu, append-only event). */

interface CounterBreakdown {
  today: number;
  week: number;
  total: number;
}

interface StatisticsSummary {
  counters: Record<string, CounterBreakdown>;
  applications: CounterBreakdown;
  streak: { current: number; longest: number };
}

interface MonthlyPoint {
  month: string; // YYYY-MM
  pomodoros: number;
  todos: number;
  bookmarks: number;
  notes: number;
  rss_read: number;
  reviews: number;
}

/** Sayac adi -> gorunen etiket. Bilinmeyen sayaclar atlanir. */
const COUNTER_LABELS: Record<string, string> = {
  pomodoros: "Pomodoro",
  todos: "Görev",
  bookmarks: "Kayıt",
  notes: "Not",
  rss_read: "Okunan",
  reviews: "Değerlendirme",
  courses: "Kurs",
};

const MONTH_NAMES = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];

function monthLabel(month: string): string {
  const [year, index] = month.split("-").map(Number);
  return `${MONTH_NAMES[index - 1]} '${String(year).slice(2)}`;
}

function MonthlyBars({ points }: { points: MonthlyPoint[] }) {
  const totals = points.map(
    (point) => point.pomodoros + point.todos + point.bookmarks + point.notes + point.rss_read + point.reviews,
  );
  const max = Math.max(1, ...totals);
  const height = 88;

  return (
    <div className="flex h-28 items-end gap-2" role="img" aria-label="Son 6 ayın toplam hareketi">
      {points.map((point, index) => (
        <div
          key={point.month}
          className="flex min-w-0 flex-1 flex-col items-center gap-1"
          title={`${monthLabel(point.month)}: ${totals[index]} hareket`}
        >
          <span className="text-micro text-muted">{totals[index] > 0 ? totals[index] : ""}</span>
          <div
            className={cx("w-full rounded-sm", totals[index] > 0 ? "bg-accent" : "bg-border")}
            style={{ height: `${Math.max(2, Math.round((totals[index] / max) * height))}px` }}
          />
          <span className="text-micro text-muted">{monthLabel(point.month)}</span>
        </div>
      ))}
    </div>
  );
}

export function StatisticsWidget() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ["statistics", "summary"],
    queryFn: () => api.get<StatisticsSummary>("/statistics/summary"),
  });
  const { data: monthly = [] } = useQuery({
    queryKey: ["statistics", "monthly", 6],
    queryFn: () => api.get<MonthlyPoint[]>("/statistics/monthly?months=6"),
  });

  if (isLoading) return <Section title="İstatistikler">…</Section>;

  const counters = Object.entries(summary?.counters ?? {})
    .filter(([name]) => name in COUNTER_LABELS)
    .filter(([, value]) => value.total > 0);
  const streak = summary?.streak.current ?? 0;
  const applicationsToday = summary?.applications.today ?? 0;

  return (
    <Section
      title="İstatistikler"
      action={
        streak > 0 ? (
          <span className="flex items-center gap-1 text-meta text-muted" title="Kesintisiz hareketli gün">
            <Flame size={13} className="text-warn" />
            {streak} gün seri
          </span>
        ) : undefined
      }
    >
      {counters.length === 0 && applicationsToday === 0 ? (
        <p className="text-meta text-muted">Henüz veri yok. Hareket ettikçe burada toplanır.</p>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {counters.map(([name, value]) => (
              <div key={name} className="rounded-card border border-subtle bg-surface px-3 py-2">
                <span className="block text-heading text-primary">{value.today}</span>
                <span className="block text-micro text-muted">bugün · {COUNTER_LABELS[name]}</span>
              </div>
            ))}
            {applicationsToday > 0 && (
              <div className="rounded-card border border-subtle bg-surface px-3 py-2">
                <span className="block text-heading text-primary">{applicationsToday}</span>
                <span className="block text-micro text-muted">bugün · Başvuru</span>
              </div>
            )}
          </div>
          {monthly.length > 0 && <MonthlyBars points={monthly} />}
        </div>
      )}
    </Section>
  );
}
