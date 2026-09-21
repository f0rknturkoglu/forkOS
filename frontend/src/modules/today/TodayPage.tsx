import type { ReactNode } from "react";
import { allTodayStats, allTodayWidgetViews } from "@/core/registry";
import { Empty, PageFrame } from "@/core/ui";
import type { TodayRegion } from "@/core/types";
import { TodayHero } from "./TodayHero";

/**
 * Home = günün yürütme ekranı.
 *
 * Yerleşim artık eski "Plan / Akış / Durum" ÜÇ SÜTUN modeline göre değil,
 * içeriğe göre kurulur (bkz. `core/types.ts` → `TodayRegion`):
 *
 *   priority   karar bekleyen işler — tam genişlik, en üstte (boşken çizilmez)
 *   main       ana çalışma bölgesi: şimdi/sırada + günün planı
 *   rail       ana bölgenin yanındaki durum şeridi: dikkat
 *   secondary  ana bölgenin ALTINDA akan ikincil yüzeyler
 *
 * Boş bölge ne çizilir ne yer tutar: varsayılan Home'da orta sütun diye bir
 * kavram olmadığı için ekranın ortasında delik oluşmaz. Sütunlar registry'den
 * beslenir; burası hiçbir modülün adını bilmez.
 */

/** Bölgelerin görünen sırası. */
const REGION_ORDER: TodayRegion[] = ["priority", "main", "rail", "secondary"];

/** Bölge başlıkları — yalnız birden fazla bölge doluyken gösterilir. */
const REGION_LABELS: Record<TodayRegion, string> = {
  priority: "Karar bekleyen",
  main: "Gün",
  rail: "Dikkat",
  secondary: "Bağlamsal",
};

function renderWidgets(views: { id: string; widget: { component: React.ComponentType } }[], region: TodayRegion) {
  return views
    .filter((view) => (view.widget as { region?: TodayRegion }).region === region)
    .map((view) => {
      const Widget = view.widget.component;
      return <Widget key={view.id} />;
    });
}

export function TodayPage() {
  const stats = allTodayStats();
  const views = allTodayWidgetViews();
  const byRegion = Object.fromEntries(REGION_ORDER.map((region) => [region, renderWidgets(views, region)])) as Record<
    TodayRegion,
    ReactNode[]
  >;
  const empty = stats.length + views.length === 0;

  if (empty) {
    return (
      <PageFrame>
        <TodayHero />
        <Empty variant="page" title="Panel boş">
          Hiçbir modül widget vermiyor. Ayarlar'dan modülleri açabilirsin.
        </Empty>
      </PageFrame>
    );
  }

  return (
    <PageFrame>
      <TodayHero
        metrics={stats.map((Tile, index) => (
          <Tile key={index} />
        ))}
      />
      <HomeRegions byRegion={byRegion} />
    </PageFrame>
  );
}

/**
 * Bölgeleri tek bir ızgaraya dizer. Şablon GÖRÜNÜR bölgelerden hesaplanır
 * (CSS değişkenleri): boş bölge yer tutmaz, kalan bölge genişler.
 */
export function HomeRegions({ byRegion }: { byRegion: Record<TodayRegion, ReactNode[]> }) {
  const hasMain = byRegion.main.length > 0;
  const hasRail = byRegion.rail.length > 0;
  const hasSecondary = byRegion.secondary.length > 0;
  const showLabels = [hasMain, hasRail, hasSecondary].filter(Boolean).length > 1;

  const style = {
    // Ana bölge esnek, şerit dar; şerit boşsa ana bölge tam genişlik.
    "--home-cols": hasMain && hasRail ? "minmax(0, 1fr) minmax(280px, 340px)" : "minmax(0, 1fr)",
    "--home-areas": hasMain && hasRail ? '"main rail"' : hasMain ? '"main"' : '"rail"',
  } as React.CSSProperties;

  return (
    <div className="home-regions" style={style}>
      {byRegion.priority.length > 0 && (
        <section className="home-priority space-y-4" aria-label={REGION_LABELS.priority}>
          {byRegion.priority}
        </section>
      )}

      {(hasMain || hasRail) && (
        <div className="home-split">
          {hasMain && (
            <section className="home-main space-y-5" aria-label={REGION_LABELS.main}>
              {showLabels && <ColumnLabel>{REGION_LABELS.main}</ColumnLabel>}
              {byRegion.main}
            </section>
          )}
          {hasRail && (
            <aside className="home-rail space-y-5" aria-label={REGION_LABELS.rail}>
              {showLabels && <ColumnLabel>{REGION_LABELS.rail}</ColumnLabel>}
              {byRegion.rail}
            </aside>
          )}
        </div>
      )}

      {hasSecondary && (
        <section className="home-secondary border-t border-subtle pt-3" aria-label={REGION_LABELS.secondary}>
          {byRegion.secondary}
        </section>
      )}
    </div>
  );
}

/** Bölge başlığı — sadece bölgeler ayrıştığında görünür. */
function ColumnLabel({ children }: { children: ReactNode }) {
  return <p className="label-caps hidden border-b border-subtle pb-1.5 md:block">{children}</p>;
}
