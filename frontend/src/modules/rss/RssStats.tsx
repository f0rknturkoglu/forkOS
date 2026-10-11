import { SummaryMetric as Metric } from "@/core/TodaySummary";
import { useRssStats } from "@/core/runtimeQueries";

/**
 * Bugun sayfasindaki RSS ozeti.
 *
 * Durustluk: sorgu gelmeden sahte sifir gosterilmez ("0 aktif besleme"
 * yaniltirdi); deger gelene kadar "–" yazilir. Backend'in `failing_feeds`
 * alani hata biriktiren YA DA kapatilmis beslemeleri sayar; etiket bunu
 * acikca soyler (kapatilmis besleme "sorunlu" diye damgalanmaz).
 */
export function RssStats() {
  // Paylasilan uç: anahtar `core/runtimeQueries`'te tek yerde durur (§78).
  const { data } = useRssStats();
  return (
    <>
      <Metric
        label="Okunmamış RSS"
        value={data?.unread ?? "–"}
        hint={data ? `${data.active_feeds} aktif besleme` : undefined}
        href="#/rss"
      />
      <Metric label="Hata / kapalı besleme" value={data?.failing_feeds ?? "–"} href="#/health" />
    </>
  );
}
