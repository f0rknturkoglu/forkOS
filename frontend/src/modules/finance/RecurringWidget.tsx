import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { RecurringPayment } from "@/core/types";
import { RowList, Section } from "@/core/ui";
import { daysBetween, todayKey } from "@/lib/date";
import { dueLabel, money } from "./financeLabels";

const RECURRING_WIDGET_KEY = ["recurring", "widget"] as const;

export function RecurringWidget() {
  const { data = [] } = useQuery({
    queryKey: RECURRING_WIDGET_KEY,
    queryFn: () => api.get<RecurringPayment[]>("/recurring-payments"),
  });
  const active = data
    .filter((x) => x.active && x.next_due_at)
    .sort((a, b) => (a.next_due_at ?? "").localeCompare(b.next_due_at ?? ""))
    .slice(0, 5);
  return (
    <Section title="Yaklaşan ödemeler">
      {active.length === 0 ? (
        <span className="text-meta text-muted">Ödeme yok.</span>
      ) : (
        <RowList>
          {active.map((x) => (
            <div key={x.id} className="flex items-baseline justify-between gap-3 py-2 text-meta">
              <span className="min-w-0 flex-1 truncate">{x.title}</span>
              <span className="shrink-0 text-muted">
                {dueLabel(daysBetween(todayKey(), x.next_due_at ?? todayKey()))}
              </span>
              <span className="numeral shrink-0 text-primary">{money(x.amount, x.currency, 0)}</span>
            </div>
          ))}
        </RowList>
      )}
    </Section>
  );
}
