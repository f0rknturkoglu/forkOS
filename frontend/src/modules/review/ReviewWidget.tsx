import { useQuery } from "@tanstack/react-query";
import { ClipboardCheck } from "lucide-react";
import { api } from "@/core/api";
import { Section, cx } from "@/core/ui";
import { navigate } from "@/app/router";
import type { ActivityEvent } from "@/core/types";

/**
 * Gunu kapatma hatirlaticisi.
 *
 * Kendi basina bir widget olmasinin sebebi: degerlendirme yapilmadigi
 * surece gorunmesi gereken TEK sey bu. Yapildiysa tek satirlik onay
 * kaliyor, panelde yer kaplamiyor.
 */
export function ReviewWidget() {
  // Gunun degerlendirmesi yapildi mi -- event'ten okunur, ayri uc gerekmez.
  const { data: events = [] } = useQuery({
    queryKey: ["activity", "review-check"],
    queryFn: () => api.get<ActivityEvent[]>("/activity?limit=40&verbs=review.completed"),
  });

  const midnight = new Date();
  midnight.setHours(0, 0, 0, 0);
  const doneToday = events.some((event) => new Date(event.occurred_at) >= midnight);

  const hour = new Date().getHours();
  // Aksama kadar hatirlatmanin anlami yok; gun daha bitmedi.
  const evening = hour >= 18 || hour < 4;

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
          {doneToday
            ? "Bugünü değerlendirdin."
            : evening
              ? "Günü kapat — bugünü değerlendir"
              : "Günlük değerlendirme"}
        </span>
        {!doneToday && <span className="shrink-0 text-meta">aç →</span>}
      </button>
    </Section>
  );
}
