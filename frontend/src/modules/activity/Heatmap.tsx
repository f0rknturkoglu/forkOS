import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Button, Section, cx, Skeleton } from "@/core/ui";
import type { Heatmap as HeatmapData, HeatmapDay } from "@/core/types";
import { formatTrDate } from "@/lib/date";
import { HeatmapPreview } from "./HeatmapPreview";

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

function previewPosition(anchor: HTMLElement) {
  const rect = anchor.getBoundingClientRect();
  const width = Math.min(288, window.innerWidth - 24);
  const above = rect.bottom + 260 > window.innerHeight;
  return {
    width,
    above,
    left: Math.max(12, Math.min(rect.left - width / 2 + rect.width / 2, window.innerWidth - width - 12)),
    top: above ? rect.top - 8 : rect.bottom + 8,
  };
}

function tooltip(entry: HeatmapDay, labels: Record<string, string>): string {
  const date = formatTrDate(entry.day, { day: "numeric", month: "long", year: "numeric" });
  if (entry.total === 0) return `${date} — kayıt yok`;
  const parts = Object.entries(entry.kinds)
    .sort((a, b) => b[1] - a[1])
    .map(([kind, count]) => `${count} ${labels[kind] ?? kind}`);
  return `${date} — ${parts.join(" · ")}`;
}

export function Heatmap({
  days = 365,
  compact = false,
  rangeControl,
}: {
  days?: number;
  compact?: boolean;
  rangeControl?: ReactNode;
}) {
  const recent = compact && days <= 31;
  const scroller = useRef<HTMLDivElement>(null);
  const previewId = useId();
  const previewAnchor = useRef<HTMLElement | null>(null);
  const closing = useRef<ReturnType<typeof setTimeout>>();
  const [preview, setPreview] = useState<{
    entry: HeatmapDay;
    left: number;
    top: number;
    above: boolean;
    width: number;
  } | null>(null);
  const cancelClose = () => clearTimeout(closing.current);
  const closeSoon = () => {
    cancelClose();
    closing.current = setTimeout(() => setPreview(null), 150);
  };
  const showPreview = (entry: HeatmapDay, anchor: HTMLElement) => {
    cancelClose();
    previewAnchor.current = anchor;
    setPreview({ entry, ...previewPosition(anchor) });
  };
  useEffect(() => {
    const close = () => {
      clearTimeout(closing.current);
      setPreview(null);
    };
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    window.addEventListener("keydown", key);
    window.addEventListener("resize", close);
    const onScroll = (event: Event) => {
      if (event.target instanceof Element && event.target.closest("[data-heatmap-preview]")) return;
      const anchor = previewAnchor.current;
      if (anchor && document.activeElement === anchor) {
        // Klavye odağı tarayıcıyı otomatik kaydırabilir; panel yeni konumu izler.
        setPreview((current) => (current ? { ...current, ...previewPosition(anchor) } : null));
      } else close();
    };
    window.addEventListener("scroll", onScroll, true);
    return () => {
      clearTimeout(closing.current);
      window.removeEventListener("keydown", key);
      window.removeEventListener("resize", close);
      window.removeEventListener("scroll", onScroll, true);
    };
  }, []);
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
        <Skeleton className="h-24 w-full" />
      </Section>
    );
  }

  // Bos/bozuk gun listesi haritayi cizemez: Home'un tamamini cokertmek
  // yerine durust bir bos durum gosterilir.
  if (!Array.isArray(data.days) || data.days.length === 0) {
    return (
      <Section title="Emek haritası">
        <p className="py-4 text-center text-meta text-muted">Haritada gösterilecek gün yok.</p>
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
      hint={compact ? undefined : `son ${Math.round(days / 30)} ay`}
      action={
        rangeControl ??
        (data.streak > 0 ? <span className="text-meta text-accent">{data.streak} gün üst üste</span> : undefined)
      }
      bodyClassName="stack-y-3 px-3.5 py-3"
    >
      {/* Gun etiketleri kaydirma ALANININ DISINDA: harita saga kayinca
          onlarla birlikte kaymasin, hangi satirin hangi gun oldugu kalsin. */}
      <div className={cx("flex gap-1", recent && "justify-center")}>
        <div className="grid shrink-0 grid-rows-7 gap-1 pr-1 pt-4 text-micro leading-[10px] text-muted">
          {WEEKDAYS.map((label, index) => (
            <span key={index} className={cx("flex items-center", recent ? "h-5" : "h-2.5")}>
              {label}
            </span>
          ))}
        </div>

        <div ref={scroller} className={cx("min-w-0 overflow-x-auto pb-1", !recent && "flex-1")}>
          <div className="inline-flex flex-col gap-1">
            <div className="flex gap-1 text-micro leading-3 text-muted">
              {monthTicks.map((tick) => (
                <span
                  key={tick.week}
                  style={{ width: `${tick.span * (recent ? 24 : 14) - 4}px` }}
                  className="shrink-0 truncate"
                >
                  {tick.label}
                </span>
              ))}
            </div>
            <div className="grid grid-flow-col grid-rows-7 gap-1">
              {cells.map((entry, index) =>
                entry === null ? (
                  <span key={`pad-${index}`} className={recent ? "h-5 w-5" : "h-2.5 w-2.5"} />
                ) : (
                  <a
                    key={entry.day}
                    href={`#/day?d=${entry.day}`}
                    aria-label={tooltip(entry, data.labels)}
                    aria-describedby={preview?.entry.day === entry.day ? previewId : undefined}
                    onMouseEnter={(event) => showPreview(entry, event.currentTarget)}
                    onMouseLeave={closeSoon}
                    onFocus={(event) => showPreview(entry, event.currentTarget)}
                    onBlur={closeSoon}
                    className={cx(
                      "rounded-control transition-colors hover:ring-2 hover:ring-accent",
                      recent ? "h-5 w-5" : "h-2.5 w-2.5",
                      STEP_BG[step(entry.total)],
                    )}
                  />
                ),
              )}
            </div>
          </div>
        </div>
      </div>

      {preview &&
        createPortal(
          <div
            id={previewId}
            role="tooltip"
            data-heatmap-preview
            className="fixed z-popover overflow-y-auto rounded-card border border-strong bg-surface-raised shadow-overlay"
            style={{
              left: preview.left,
              top: preview.top,
              width: preview.width,
              maxHeight: Math.max(80, (preview.above ? preview.top : window.innerHeight - preview.top) - 12),
              transform: preview.above ? "translateY(-100%)" : undefined,
            }}
            onMouseEnter={cancelClose}
            onMouseLeave={closeSoon}
            onFocus={cancelClose}
            onBlur={closeSoon}
          >
            <HeatmapPreview key={preview.entry.day} entry={preview.entry} labels={data.labels} />
          </div>,
          document.body,
        )}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-subtle pt-2.5 text-meta text-muted">
        {!compact && (
          <span>
            <span className="text-primary">{data.total}</span> kayıt ·{" "}
            <span className="text-primary">{data.active_days}</span> aktif gün
          </span>
        )}
        <span className="ml-auto flex items-center gap-1">
          az
          {STEP_BG.map((bg) => (
            <span key={bg} className={cx("h-2.5 w-2.5 rounded-[2px]", bg)} />
          ))}
          çok
        </span>
      </div>

      {!compact && Object.keys(data.totals).length > 0 && (
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

/**
 * Home varsayılan olarak son 30 günü gösterir; yıl görünümü açık seçimdir.
 */
export function HomeHeatmap() {
  const [expanded, setExpanded] = useState(false);
  return (
    <Heatmap
      compact
      days={expanded ? 365 : 30}
      rangeControl={
        <Button size="sm" variant="ghost" ariaPressed={expanded} onClick={() => setExpanded((value) => !value)}>
          {expanded ? "Son ay" : "Tüm aylar"}
        </Button>
      }
    />
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
        label: formatTrDate(entry.day, { month: "short" }),
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
