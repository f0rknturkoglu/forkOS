import type { ReactNode } from "react";
import { allTodayStats, allTodayWidgetsIn } from "@/core/registry";
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
  const left = allTodayWidgetsIn("left");
  const center = allTodayWidgetsIn("center");
  const right = allTodayWidgetsIn("right");
  const empty = stats.length + left.length + center.length + right.length === 0;

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
      center={center.map((Widget, index) => (
        <Widget key={index} />
      ))}
      left={left.map((Widget, index) => (
        <Widget key={index} />
      ))}
      right={right.map((Widget, index) => (
        <Widget key={index} />
      ))}
      labelled
    />
  );
}

/** Sutun basligi -- sadece sutunlarin ayristigi genislikte gorunur. */
function ColumnLabel({ children }: { children: ReactNode }) {
  return <p className="label-caps hidden border-b border-subtle pb-1.5 md:block">{children}</p>;
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
  return (
    <PageFrame>
      {hero}
      <div className="dashboard-grid">
        <main className="dashboard-main space-y-5">
          {labelled && center.length > 0 && <ColumnLabel>{COLUMN_LABELS.center}</ColumnLabel>}
          {center}
        </main>
        <aside className="dashboard-left space-y-5">
          {labelled && left.length > 0 && <ColumnLabel>{COLUMN_LABELS.left}</ColumnLabel>}
          {left}
        </aside>
        <aside className="dashboard-right space-y-5">
          {labelled && right.length > 0 && <ColumnLabel>{COLUMN_LABELS.right}</ColumnLabel>}
          {right}
        </aside>
      </div>
    </PageFrame>
  );
}
