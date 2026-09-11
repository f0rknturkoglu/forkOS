import { useState } from "react";
import type { MonthlyPoint } from "@/core/types";
import { cx } from "@/core/ui";

const MONTH_NAMES = [
  "Ocak",
  "Şubat",
  "Mart",
  "Nisan",
  "Mayıs",
  "Haziran",
  "Temmuz",
  "Ağustos",
  "Eylül",
  "Ekim",
  "Kasım",
  "Aralık",
];

const MONTH_SHORT = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];

export function monthLabel(month: string): string {
  const [year, index] = month.split("-").map(Number);
  return `${MONTH_SHORT[index - 1]} '${String(year).slice(2)}`;
}

function monthLabelLong(month: string): string {
  const [year, index] = month.split("-").map(Number);
  return `${MONTH_NAMES[index - 1]} ${year}`;
}

interface ActivityBreakdown {
  focus: number;
  tasks: number;
  reading: number;
  career: number;
  total: number;
}

export function calculateBreakdown(point: MonthlyPoint): ActivityBreakdown {
  const focus = point.pomodoros;
  const tasks = point.todos;
  const reading = point.bookmarks + point.rss_read + point.notes;
  const career = point.applications + point.reviews;
  return {
    focus,
    tasks,
    reading,
    career,
    total: focus + tasks + reading + career,
  };
}

export function RhythmChart({
  points,
  compact = false,
  className,
}: {
  points: MonthlyPoint[];
  compact?: boolean;
  className?: string;
}) {
  const [hoveredMonth, setHoveredMonth] = useState<string | null>(null);

  const breakdowns = points.map(calculateBreakdown);
  const totals = breakdowns.map((b) => b.total);
  const max = Math.max(1, ...totals);
  const chartHeightPx = compact ? 80 : 120;

  const activePoint = points.find((p) => p.month === hoveredMonth);
  const activeBreakdown = activePoint ? calculateBreakdown(activePoint) : null;

  return (
    <div className={cx("relative space-y-3", className)}>
      {/* Popover / Detay Kartı */}
      {activeBreakdown && activePoint && (
        <div
          role="tooltip"
          className="absolute -top-14 left-1/2 z-dropdown -translate-x-1/2 rounded-card border border-subtle bg-surface p-2.5 shadow-raised transition-all animate-in fade-in"
        >
          <div className="flex items-center justify-between gap-4 border-b border-subtle pb-1.5">
            <span className="text-meta font-medium text-primary">{monthLabelLong(activePoint.month)}</span>
            <span className="text-micro font-semibold text-accent">{activeBreakdown.total} toplam hareket</span>
          </div>
          <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 text-micro">
            <div className="flex items-center gap-1.5 text-secondary">
              <span className="h-2 w-2 shrink-0 rounded-full bg-accent" />
              <span>{activeBreakdown.focus} Odak</span>
            </div>
            <div className="flex items-center gap-1.5 text-secondary">
              <span className="h-2 w-2 shrink-0 rounded-full bg-ok" />
              <span>{activeBreakdown.tasks} Görev</span>
            </div>
            <div className="flex items-center gap-1.5 text-secondary">
              <span className="h-2 w-2 shrink-0 rounded-full bg-info" />
              <span>{activeBreakdown.reading} Okuma</span>
            </div>
            <div className="flex items-center gap-1.5 text-secondary">
              <span className="h-2 w-2 shrink-0 rounded-full bg-primary/70" />
              <span>{activeBreakdown.career} Başvuru</span>
            </div>
          </div>
        </div>
      )}

      {/* Sütun Grafiği */}
      <div
        className={cx("flex items-end gap-2 sm:gap-3", compact ? "h-28" : "h-36")}
        role="img"
        aria-label="Son ayların toplam hareketi"
      >
        {points.map((point, index) => {
          const b = breakdowns[index];
          const isHovered = hoveredMonth === point.month;
          const barHeight = b.total > 0 ? Math.max(6, Math.round((b.total / max) * chartHeightPx)) : 2;

          return (
            <div
              key={point.month}
              data-testid="rhythm-month-bar"
              tabIndex={0}
              title={
                `${monthLabel(point.month)}: ${b.total} hareket\n` +
                `odak ${point.pomodoros} · görev ${point.todos} · ` +
                `okuma ${point.rss_read + point.bookmarks} · başvuru ${point.applications}`
              }
              onMouseEnter={() => setHoveredMonth(point.month)}
              onMouseLeave={() => setHoveredMonth((current) => (current === point.month ? null : current))}
              onFocus={() => setHoveredMonth(point.month)}
              onBlur={() => setHoveredMonth((current) => (current === point.month ? null : current))}
              className="group flex min-w-0 flex-1 cursor-pointer flex-col items-center gap-1.5 outline-none"
            >
              {/* Sayı Göstergesi */}
              <span
                className={cx(
                  "text-micro tabular-nums transition-colors",
                  isHovered ? "font-semibold text-primary" : "text-muted",
                  b.total === 0 && "opacity-0",
                )}
              >
                {b.total > 0 ? b.total : ""}
              </span>

              {/* Çok Katmanlı Bar */}
              <div
                className={cx(
                  "flex w-full flex-col-reverse overflow-hidden rounded-t-control border transition-all duration-200",
                  isHovered ? "scale-[1.02] border-strong shadow-raised" : "border-transparent",
                  b.total === 0 ? "bg-subtle" : "bg-surface-sunken",
                )}
                style={{ height: `${barHeight}px` }}
              >
                {b.total > 0 ? (
                  <>
                    {b.focus > 0 && (
                      <div
                        className="w-full bg-accent transition-all"
                        style={{ height: `${(b.focus / b.total) * 100}%` }}
                        title={`${b.focus} Odak`}
                      />
                    )}
                    {b.tasks > 0 && (
                      <div
                        className="w-full bg-ok transition-all"
                        style={{ height: `${(b.tasks / b.total) * 100}%` }}
                        title={`${b.tasks} Görev`}
                      />
                    )}
                    {b.reading > 0 && (
                      <div
                        className="w-full bg-info transition-all"
                        style={{ height: `${(b.reading / b.total) * 100}%` }}
                        title={`${b.reading} Okuma`}
                      />
                    )}
                    {b.career > 0 && (
                      <div
                        className="w-full bg-primary/70 transition-all"
                        style={{ height: `${(b.career / b.total) * 100}%` }}
                        title={`${b.career} Başvuru`}
                      />
                    )}
                  </>
                ) : (
                  <div className="h-full w-full bg-subtle" />
                )}
              </div>

              {/* Ay Etiketi */}
              <span
                className={cx("text-micro transition-colors", isHovered ? "font-semibold text-primary" : "text-muted")}
              >
                {monthLabel(point.month)}
              </span>
            </div>
          );
        })}
      </div>

      {/* Lejant (Kompakt modda gizli) */}
      {!compact && (
        <div className="flex flex-wrap items-center justify-center gap-3 pt-1 text-micro text-muted">
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-accent" /> Odak
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-ok" /> Görev
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-info" /> Okuma & Not
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-primary/70" /> Başvuru
          </span>
        </div>
      )}
    </div>
  );
}
