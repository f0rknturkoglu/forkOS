import { allTodayStats, useTodayWidgetViews } from "@/core/registry";
import type { TodayWidgetView } from "@/core/registry";
import { Empty, PageFrame, cx } from "@/core/ui";
import type { TodayPlacement } from "@/core/types";
import { TodayHero } from "./TodayHero";

/**
 * Home = günün yürütme ekranı.
 *
 * İskelet sabittir ve TEK kaynaktan gelir (`core/types.ts` → `TodayPlacement`):
 * hero, ardından bekleyen kararlar şeridi ve masaüstünde üç kolon
 *
 *   sol    bugünün planı + öğrenme
 *   orta   okuma akışı + ısı haritası (görsel çapa)
 *   sağ    son tarihler + kariyer
 *
 * Dar ekranda ızgara tek kolona düşer ve DOM sırası okunur: bekleyen kararlar →
 * bugünün planı → son tarihler → kariyer → okuma akışı → öğrenme → ısı haritası.
 * Yani kaydırma sırası, ekran okuyucu sırası ve masaüstü kolonları AYNI
 * sözleşmeden türer; ikinci bir "mobil düzen" yok.
 *
 * Widget'ları Home bilmez: hangi yüzeyin çekirdek olduğunu ve hangi kolona
 * düştüğünü modül kaydı söyler (`TodayWidget.core`). Çekirdek olmayan yüzeyler
 * iskeletin ALTINDA akar.
 */

/** Kolon yerleşimi: masaüstünde açık kolon, dar ekranda tek kolon (DOM sırası). */
const PLACEMENT_CLASS: Record<TodayPlacement, string> = {
  priority: "lg:col-span-full",
  left: "lg:col-start-1",
  center: "lg:col-start-2",
  right: "lg:col-start-3",
};

export function TodayPage() {
  const stats = allTodayStats();
  const views = useTodayWidgetViews();

  if (stats.length + views.length === 0) {
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
      <HomeGrid views={views} />
    </PageFrame>
  );
}

/**
 * İskelet ızgarası. Masaüstünde üç kolon (`grid-auto-flow: row dense`):
 * her yüzey kendi kolonuna yerleşir, sırası `order` ile sabittir. Dar ekranda
 * tek kolon; sıra değişmez.
 *
 * Kendini çizmeyen yüzey (veri yokken null dönen kart) ızgarada yer TUTMAZ:
 * `empty:hidden` boş sarmalayıcıyı düşürür, kalanlar boşluğu kapatır.
 */
export function HomeGrid({ views }: { views: TodayWidgetView[] }) {
  return (
    <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[minmax(13rem,0.9fr)_minmax(0,1.5fr)_minmax(13rem,0.9fr)] lg:[grid-auto-flow:row_dense]">
      {views.map((view) => {
        const Widget = view.widget.component;
        return (
          <div
            key={view.id}
            className={cx("min-w-0 empty:hidden", view.widget.core && PLACEMENT_CLASS[view.widget.core])}
          >
            <Widget />
          </div>
        );
      })}
    </div>
  );
}
