import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useState,
  type ComponentProps,
  type ComponentType,
} from "react";
import { Metric } from "./ui";

const SummaryCounts = createContext<((id: string, value: number | null) => void) | null>(null);

/** Modül sayıları yalnız kendi sorgularından gelir; ikinci istek veya DOM okuması yok. */
export function SummaryMetric(props: ComponentProps<typeof Metric>) {
  const report = useContext(SummaryCounts);
  const id = useId();
  const count = typeof props.value === "number" && Number.isFinite(props.value) ? Math.max(0, props.value) : null;
  useEffect(() => {
    report?.(id, count);
    return () => report?.(id, null);
  }, [report, id, count]);
  return <Metric {...props} />;
}

export function TodaySummary({ stats }: { stats: ComponentType[] }) {
  const [counts, setCounts] = useState<Record<string, number>>({});
  const report = useCallback((id: string, value: number | null) => {
    setCounts((current) => {
      if (value === null && !(id in current)) return current;
      if (value !== null && current[id] === value) return current;
      const next = { ...current };
      if (value === null) delete next[id];
      else next[id] = value;
      return next;
    });
  }, []);
  const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
  return (
    <SummaryCounts.Provider value={report}>
      <details
        className="text-meta"
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            event.currentTarget.open = false;
            event.currentTarget.querySelector("summary")?.focus();
          }
        }}
      >
        <summary className="daily-summary-trigger flex cursor-pointer list-none items-center gap-1.5 rounded-control px-2 py-1 text-muted hover:text-primary">
          Günlük özet
          {total > 0 && (
            <span
              aria-label={`${total} toplam`}
              className="flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-micro font-medium leading-none text-canvas"
            >
              {total > 99 ? "99+" : total}
            </span>
          )}
        </summary>
        <section
          aria-label="Günlük kısa özet"
          className="today-summary absolute left-0 top-full z-popover mt-2 w-64 rounded-card border border-subtle bg-surface p-3 shadow-card sm:left-auto sm:right-0"
        >
          {stats.map((Tile, index) => (
            <Tile key={index} />
          ))}
        </section>
      </details>
    </SummaryCounts.Provider>
  );
}
