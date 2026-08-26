import { useQuery } from "@tanstack/react-query";
import { CalendarCheck, ClipboardCheck } from "lucide-react";
import { api } from "@/core/api";
import { Section, cx } from "@/core/ui";
import { navigate } from "@/app/router";
import type { ActivityEvent } from "@/core/types";

interface ReviewOut {
  id: string;
  kind: "daily" | "weekly";
  period_start: string;
  period_end: string;
}

/** Bu haftanin Pazartesi'si (haftalik degerlendirme donemi baslangici). */
function mondayOf(date: Date): Date {
  const day = date.getDay(); // 0 = Pazar
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(date);
  monday.setDate(date.getDate() + diff);
  monday.setHours(0, 0, 0, 0);
  return monday;
}

const isoDay = (date: Date) => date.toLocaleDateString("sv-SE");

/**
 * Gunu kapatma hatirlaticisi + haftalik degerlendirme giris noktasi.
 *
 * Review modulu nav'da gizli (Faz 10); ASIL giris yeri bu widget.
 * Gereksiz hatirlatma yok: gunluk aksama kadar bekler, haftalik sadece
 * haftanin ilk/son gunu hatirlatir, ikisi de yapildiginda tek satira iner.
 */
export function ReviewWidget() {
  // Gunun degerlendirmesi yapildi mi -- event'ten okunur, ayri uc gerekmez.
  const { data: events = [] } = useQuery({
    queryKey: ["activity", "review-check"],
    queryFn: () => api.get<ActivityEvent[]>("/activity?limit=40&verbs=review.completed"),
  });
  const { data: reviews = [] } = useQuery({
    queryKey: ["reviews", "weekly"],
    queryFn: () => api.get<ReviewOut[]>("/reviews?kind=weekly&limit=5"),
  });

  const midnight = new Date();
  midnight.setHours(0, 0, 0, 0);
  const doneToday = events.some((event) => new Date(event.occurred_at) >= midnight);

  const now = new Date();
  const hour = now.getHours();
  // Aksama kadar hatirlatmanin anlami yok; gun daha bitmedi.
  const evening = hour >= 18 || hour < 4;

  // Haftalik: bu haftanin donemi (Pazartesi) kayitli mi? Hafta donumu
  // Pazar/Pazartesi -- hatirlatma yalniz bu iki gunde cikar.
  const weekStart = isoDay(mondayOf(now));
  const doneThisWeek = reviews.some((r) => r.period_start === weekStart);
  const weekday = now.getDay();
  const weekTurn = weekday === 0 || weekday === 1;

  return (
    <Section title="Değerlendirme">
      <button
        type="button"
        onClick={() => navigate("/review/daily")}
        className={cx(
          "flex w-full items-center gap-2.5 rounded-control border px-3 py-2.5 text-left transition",
          doneToday
            ? "border-ok-border bg-ok-surface text-ok"
            : evening
              ? "border-accent-border bg-accent-surface text-accent hover:brightness-95"
              : "border-subtle text-secondary hover:border-strong hover:text-primary",
        )}
      >
        <ClipboardCheck size={15} className="shrink-0" />
        <span className="min-w-0 flex-1 text-body">
          {doneToday ? "Bugünü değerlendirdin." : evening ? "Günü kapat — bugünü değerlendir" : "Günlük değerlendirme"}
        </span>
        {!doneToday && <span className="shrink-0 text-meta">aç →</span>}
      </button>

      <button
        type="button"
        onClick={() => navigate("/review/weekly")}
        className={cx(
          "mt-1.5 flex w-full items-center gap-2.5 rounded-control border px-3 py-2.5 text-left transition",
          doneThisWeek
            ? "border-ok-border bg-ok-surface text-ok"
            : weekTurn
              ? "border-accent-border bg-accent-surface text-accent hover:brightness-95"
              : "border-subtle text-secondary hover:border-strong hover:text-primary",
        )}
      >
        <CalendarCheck size={15} className="shrink-0" />
        <span className="min-w-0 flex-1 text-body">
          {doneThisWeek
            ? "Haftalık değerlendirmeyi yaptın."
            : weekTurn
              ? "Haftalık değerlendirme hazır — haftayı kapat"
              : "Haftalık değerlendirme"}
        </span>
        {!doneThisWeek && <span className="shrink-0 text-meta">aç →</span>}
      </button>
    </Section>
  );
}
