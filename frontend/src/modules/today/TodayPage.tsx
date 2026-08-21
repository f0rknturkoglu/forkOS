import type { ComponentType } from "react";
import { allTodayStats, todayWidgetsIn } from "@/core/registry";
import { Empty, SectionHeader } from "@/core/ui";

/**
 * Today hicbir modulu bilmez. Widget'lar registry'den gelir; hangi bolgeye
 * dusecekleri modulun kendi kaydinda yazar (todayWidgets: [{ component, zone }]).
 *
 * Uc bolge -- sayfanin agirligi yukaridan asagi azalir:
 *   Su an       tek satirda suren is, siradaki blok, bugunun gorevleri
 *   Bekleyenler islenmeyi bekleyen yiginlar; once sayilar, sonra detay
 *   Ritim       alistirmalar, degerlendirme, gecmis
 */

function Zone({
  label, hint, widgets, columns, children,
}: {
  label: string;
  hint?: string;
  widgets: ComponentType[];
  columns: string;
  children?: React.ReactNode;
}) {
  if (widgets.length === 0 && !children) return null;
  return (
    <section>
      <SectionHeader label={label} hint={hint} />
      {children}
      {widgets.length > 0 && (
        <div className={`grid gap-4 ${columns}`}>
          {widgets.map((Widget, i) => <Widget key={i} />)}
        </div>
      )}
    </section>
  );
}

export function TodayPage() {
  const stats = allTodayStats();
  const now = todayWidgetsIn("now");
  const pending = todayWidgetsIn("pending");
  const rhythm = todayWidgetsIn("rhythm");
  const empty = stats.length + now.length + pending.length + rhythm.length === 0;

  if (empty) {
    return (
      <div className="p-8">
        <Empty variant="page" title="Bugün ekranı boş">
          Hiçbir modül Today’e widget vermiyor. Ayarlar’dan modülleri açabilir,
          ya da bir modülün kaydına <code className="font-mono text-meta">todayWidgets</code> ekleyebilirsin.
        </Empty>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8 p-8">
      <Zone
        label="Şu an"
        widgets={now}
        columns="md:grid-cols-2 xl:grid-cols-3"
      />

      <Zone
        label="Bekleyenler"
        widgets={pending}
        columns="md:grid-cols-2 xl:grid-cols-3"
      >
        {stats.length > 0 && (
          <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
            {stats.map((Tile, i) => <Tile key={i} />)}
          </div>
        )}
      </Zone>

      <Zone
        label="Ritim"
        widgets={rhythm}
        columns="md:grid-cols-2 xl:grid-cols-3"
      />
    </div>
  );
}
