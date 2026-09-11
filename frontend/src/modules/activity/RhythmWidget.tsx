import { useQuery } from "@tanstack/react-query";
import { Flame } from "lucide-react";
import { api } from "@/core/api";
import { Section, cx } from "@/core/ui";
import type { MonthlyPoint, StatisticsSummary } from "@/core/types";

/**
 * Ritim ozeti: sayaclar + aylik hareket barlari.
 *
 * Etkinlik modulu ile AYNI sayaclari okur (backend'de tek katalog:
 * app/modules/statistics/service.VERB_COUNTERS) -- bugun panelindeki widget ve
 * Etkinlik & Ritim sayfasi ayni sayiyi gostersin. Sorgu anahtarlari "activity"
 * ailesindedir: yazma olaylari zaten "activity" anahtarini gecersiz kilar
 * (bkz. core/invalidation.ts), ayrica harita ile birlikte tazelenir.
 */

/** Sayac adi -> gorunen etiket. Bilinmeyen sayaclar atlanir. */
const COUNTER_LABELS: Record<string, string> = {
  pomodoros: "Pomodoro",
  todos: "Görev",
  routines: "Rutin",
  bookmarks: "Kayıt",
  bookmark_reads: "Okunan kayıt",
  rss_read: "Okunan",
  rss_saved: "Kaydedilen",
  reviews: "Değerlendirme",
  studies: "Konu",
  books: "Kitap",
  courses: "Kurs",
  media: "Medya",
  notes: "Not",
  flashcards: "Kart",
};

import { RhythmChart, monthLabel, calculateBreakdown } from "./RhythmChart";

export { monthLabel };

export const monthTotal = (point: MonthlyPoint): number => calculateBreakdown(point).total;

/** Geriye donuk uyumluluk icin MonthlyBars wrapper'i */
export function MonthlyBars({ points }: { points: MonthlyPoint[] }) {
  return <RhythmChart points={points} />;
}

export function useRhythmSummary() {
  const { data, isLoading } = useQuery({
    queryKey: ["activity", "summary"],
    queryFn: () => api.get<StatisticsSummary>("/statistics/summary"),
  });
  const { data: monthly = [] } = useQuery({
    queryKey: ["activity", "monthly", 6],
    queryFn: () => api.get<MonthlyPoint[]>("/statistics/monthly?months=6"),
  });
  return { summary: data, monthly, isLoading };
}

/** Gun panelindeki ozet widget'i: bugunun sayaclari + aylik trend. */
export function RhythmWidget() {
  const { summary, monthly, isLoading } = useRhythmSummary();

  if (isLoading) return <Section title="Ritim">…</Section>;

  const counters = Object.entries(summary?.counters ?? {})
    .filter(([name]) => name in COUNTER_LABELS)
    .filter(([, value]) => value.total > 0);
  const streak = summary?.streak.current ?? 0;
  const applicationsToday = summary?.applications.today ?? 0;

  return (
    <Section
      title="Ritim"
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
          {monthly.length > 0 && <RhythmChart points={monthly} compact />}
        </div>
      )}
    </Section>
  );
}
