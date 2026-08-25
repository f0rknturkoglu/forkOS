import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Section, cx } from "@/core/ui";
import type { Heatmap as HeatmapData, HeatmapDay } from "@/core/types";

/**
 * Emek haritasi: son bir yilin gunluk kutulari.
 *
 * Sayilan sey GitHub commit'i degil; okudugun yazi, bitirdigin gorev,
 * tamamladigin odak, isaretledigin alistirma. Hangi fiilin sayildigi
 * backend'de tek yerde duruyor (app/core/contributions.py) -- worker'in
 * kendi kayitlari (feed cekimi, hata) haritaya girmez.
 *
 * Her kare o gunun sayfasina (#/day?d=...) gider.
 */

/** Gunluk toplam -> renk basamagi. Esikler tek bir gunun makul is hacmine gore. */
function step(total: number): 0 | 1 | 2 | 3 | 4 {
  if (total === 0) return 0;
  if (total < 3) return 1;
  if (total < 8) return 2;
  if (total < 16) return 3;
  return 4;
}

const STEP_BG = ["bg-heat-0", "bg-heat-1", "bg-heat-2", "bg-heat-3", "bg-heat-4"] as const;

const WEEKDAYS = ["Pzt", "", "Çar", "", "Cum", "", "Paz"];

function tooltip(entry: HeatmapDay, labels: Record<string, string>): string {
  const date = new Date(entry.day).toLocaleDateString("tr-TR", {
    day: "numeric", month: "long", year: "numeric",
  });
  if (entry.total === 0) return `${date} — kayıt yok`;
  const parts = Object.entries(entry.kinds)
    .sort((a, b) => b[1] - a[1])
    .map(([kind, count]) => `${count} ${labels[kind] ?? kind}`);
  return `${date} — ${parts.join(" · ")}`;
}

export function Heatmap({ days = 365 }: { days?: number }) {
  const scroller = useRef<HTMLDivElement>(null);
  const { data } = useQuery({
    queryKey: ["activity", "heatmap", days],
    queryFn: () => api.get<HeatmapData>(`/activity/heatmap${qs({ days })}`),
    staleTime: 5 * 60_000,
  });

  // Yil bir ekrana sigmiyor. Ilgi cekici uc BUGUN, yani sag uc -- harita
  // gelir gelmez oraya kaydirilir, yoksa kullanici gecen agustosa bakiyor.
  useEffect(() => {
    const node = scroller.current;
    if (node) node.scrollLeft = node.scrollWidth;
  }, [data]);

  if (!data) {
    return (
      <Section title="Emek haritası">
        <p className="py-4 text-center text-meta text-muted">Yükleniyor…</p>
      </Section>
    );
  }

  // Grid haftalara bolunur: ilk sutun pazartesiden baslasin diye basa bos
  // hucre eklenir (getDay: 0=pazar -> 6, 1=pazartesi -> 0).
  const first = new Date(data.days[0].day);
  const pad = (first.getDay() + 6) % 7;
  const cells: (HeatmapDay | null)[] = [...Array<null>(pad).fill(null), ...data.days];

  const monthTicks = monthLabels(data.days, pad);

  return (
    <Section
      title="Emek haritası"
      hint={`son ${Math.round(days / 30)} ay`}
      action={
        data.streak > 0 ? (
          <span className="text-meta text-accent">{data.streak} gün üst üste</span>
        ) : undefined
      }
      bodyClassName="space-y-3 px-3.5 py-3"
    >
      {/* Gun etiketleri kaydirma ALANININ DISINDA: harita saga kayinca
          onlarla birlikte kaymasin, hangi satirin hangi gun oldugu kalsin. */}
      <div className="flex gap-1">
        <div className="grid shrink-0 grid-rows-7 gap-1 pr-1 pt-4 text-micro leading-[10px] text-muted">
          {WEEKDAYS.map((label, index) => (
            <span key={index} className="flex h-2.5 items-center">{label}</span>
          ))}
        </div>

        <div ref={scroller} className="min-w-0 flex-1 overflow-x-auto pb-1">
          <div className="inline-flex flex-col gap-1">
            <div className="flex gap-1 text-micro leading-3 text-muted">
              {monthTicks.map((tick) => (
                <span
                  key={tick.week}
                  style={{ width: `${tick.span * 14 - 4}px` }}
                  className="shrink-0 truncate"
                >
                  {tick.label}
                </span>
              ))}
            </div>
            <div className="grid grid-flow-col grid-rows-7 gap-1">
              {cells.map((entry, index) =>
                entry === null ? (
                  <span key={`pad-${index}`} className="h-2.5 w-2.5" />
                ) : (
                  <a
                    key={entry.day}
                    href={`#/day?d=${entry.day}`}
                    title={tooltip(entry, data.labels)}
                    aria-label={tooltip(entry, data.labels)}
                    className={cx(
                      "h-2.5 w-2.5 rounded-[2px] transition hover:ring-2 hover:ring-accent",
                      STEP_BG[step(entry.total)],
                    )}
                  />
                ),
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-subtle pt-2.5 text-meta text-muted">
        <span>
          <span className="text-primary">{data.total}</span> kayıt ·{" "}
          <span className="text-primary">{data.active_days}</span> aktif gün
        </span>
        <span className="ml-auto flex items-center gap-1">
          az
          {STEP_BG.map((bg) => (
            <span key={bg} className={cx("h-2.5 w-2.5 rounded-[2px]", bg)} />
          ))}
          çok
        </span>
      </div>

      {Object.keys(data.totals).length > 0 && (
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-meta text-muted">
          {Object.entries(data.totals)
            .sort((a, b) => b[1] - a[1])
            .map(([kind, count]) => (
              <li key={kind}>
                <span className="text-primary">{count}</span> {data.labels[kind] ?? kind}
              </li>
            ))}
        </ul>
      )}
    </Section>
  );
}

/** Ay adlarini basladiklari haftanin ustune yerlestirir. */
function monthLabels(days: HeatmapDay[], pad: number): { week: number; span: number; label: string }[] {
  const ticks: { week: number; span: number; label: string }[] = [];
  let current = -1;
  days.forEach((entry, index) => {
    const week = Math.floor((index + pad) / 7);
    const month = new Date(entry.day).getMonth();
    if (month !== current) {
      current = month;
      ticks.push({
        week,
        span: 0,
        label: new Date(entry.day).toLocaleDateString("tr-TR", { month: "short" }),
      });
    }
  });
  const lastWeek = Math.floor((days.length - 1 + pad) / 7);
  ticks.forEach((tick, index) => {
    tick.span = (ticks[index + 1]?.week ?? lastWeek + 1) - tick.week;
  });
  // Cok dar kalan ilk etiket yaniltici olur -- gizle.
  return ticks.filter((tick) => tick.span >= 2);
}
