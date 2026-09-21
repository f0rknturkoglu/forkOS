import type { ReactNode } from "react";
import { allTodayStats, allTodayWidgetViews } from "@/core/registry";
import { Empty, PageFrame } from "@/core/ui";
import { TodayHero } from "./TodayHero";

/**
 * Bugun = panel + gunluk gorevler. Uc sutun, her birinin tek bir isi var:
 *
 *   sol  "Plan"  — bugun ne yapacaksin: takvim, gorevler, odak, alistirma
 *   orta "Akış"  — ne oluyor: Hacker News, Reddit, RSS, GitHub
 *   sag  "Durum" — bekleyen ve olculen: hava, son tarih, gelen kutusu, sunucu
 *
 * Saat, hava ve gunun sayilari tek ust kutuda (TodayHero) -- yerleri modul
 * eklendikce kaymasin ve panelin ustunde ust uste bant olusmasin diye. Sutunlar registry'den beslenir: modul `slot` der, burasi
 * hicbir modulun adini bilmez.
 */

const COLUMN_LABELS = { left: "Plan", center: "Akış", right: "Durum" } as const;

export function TodayPage() {
  const stats = allTodayStats();
  const views = allTodayWidgetViews();
  const left = views.filter((view) => (view.widget.slot ?? "center") === "left");
  const center = views.filter((view) => (view.widget.slot ?? "center") === "center");
  const right = views.filter((view) => (view.widget.slot ?? "center") === "right");
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
    <DashboardLayout
      hero={
        <TodayHero
          metrics={stats.map((Tile, index) => (
            <Tile key={index} />
          ))}
        />
      }
      center={center.map((view) => {
        const Widget = view.widget.component;
        return <Widget key={view.id} />;
      })}
      left={left.map((view) => {
        const Widget = view.widget.component;
        return <Widget key={view.id} />;
      })}
      right={right.map((view) => {
        const Widget = view.widget.component;
        return <Widget key={view.id} />;
      })}
      labelled
    />
  );
}

/** Sutun basligi -- sadece sutunlarin ayristigi genislikte gorunur. */
function ColumnLabel({ children }: { children: ReactNode }) {
  return <p className="label-caps hidden border-b border-subtle pb-1.5 md:block">{children}</p>;
}

/**
 * Izgara şablonu GÖRÜNÜR sütunlardan türetilir.
 *
 * Ürünleştirme sonrası temiz kurulumda orta sütun (Akış) varsayılan gizlidir:
 * üç sütunluk sabit şablon o durumda ekranın ortasında kocaman bir delik
 * bırakıyordu. Boş sütunlar artık ne render edilir ne de yer tutar.
 */
function gridTemplate(present: { left: boolean; center: boolean; right: boolean }): {
  wide: string;
  areas: string;
  tablet: string;
  tabletAreas: string;
} {
  const columns = [present.left && "left", present.center && "main", present.right && "right"].filter(
    Boolean,
  ) as string[];
  if (columns.length === 3) {
    return {
      wide: "300px minmax(0, 1fr) 300px",
      areas: "left main right",
      tablet: "minmax(0, 1fr) 280px",
      tabletAreas: 'left main" "right main',
    };
  }
  if (columns.length === 2) {
    const [first, second] = columns;
    // Orta sütun yoksa ilk sütun esnek olur: iki sabit sütun geniş ekranda
    // yine delik bırakırdı.
    const flexible = first === "main" ? first : second === "main" ? "main" : first;
    // Yan sütunlar akış varken 300px (üç sütunlu düzenle aynı), akış yokken
    // 320px: esnek sütun planı taşır, durum sütunu dar kalır.
    const side = present.center ? "300px" : "320px";
    const width = (name: string) => (name === flexible || name === "main" ? "minmax(0, 1fr)" : side);
    return {
      wide: `${width(first)} ${width(second)}`,
      areas: `${first} ${second}`,
      tablet: first === "main" || second === "main" ? `${width(first)} ${width(second)}` : "minmax(0, 1fr) 320px",
      tabletAreas: `${first} ${second}`,
    };
  }
  const only = columns[0] ?? "main";
  return { wide: "minmax(0, 1fr)", areas: only, tablet: "minmax(0, 1fr)", tabletAreas: only };
}

export function DashboardLayout({
  hero,
  center,
  left,
  right,
  labelled = false,
}: {
  hero?: ReactNode;
  center: ReactNode[];
  left: ReactNode[];
  right: ReactNode[];
  labelled?: boolean;
}) {
  const present = { left: left.length > 0, center: center.length > 0, right: right.length > 0 };
  const template = gridTemplate(present);
  const style = {
    "--dash-cols": template.wide,
    "--dash-areas": template.areas,
    "--dash-cols-md": template.tablet,
    "--dash-areas-md": template.tabletAreas,
  } as React.CSSProperties;

  return (
    <PageFrame>
      {hero}
      <div className="dashboard-grid" style={style}>
        {present.left && (
          <section className="dashboard-left space-y-5" aria-label={COLUMN_LABELS.left}>
            {labelled && <ColumnLabel>{COLUMN_LABELS.left}</ColumnLabel>}
            {left}
          </section>
        )}
        {present.center && (
          <section className="dashboard-main space-y-5" aria-label={COLUMN_LABELS.center}>
            {labelled && <ColumnLabel>{COLUMN_LABELS.center}</ColumnLabel>}
            {center}
          </section>
        )}
        {present.right && (
          <aside className="dashboard-right space-y-5" aria-label={COLUMN_LABELS.right}>
            {labelled && <ColumnLabel>{COLUMN_LABELS.right}</ColumnLabel>}
            {right}
          </aside>
        )}
      </div>
    </PageFrame>
  );
}
