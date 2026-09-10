import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import type { Expense, Income } from "@/core/types";
import { Chip, Empty, FilterChip, Input, RowList, Section, cx } from "@/core/ui";
import { daysBetween, todayKey } from "@/lib/date";
import { EditTransactionDialog, type EditableTransaction } from "./EditTransactionDialog";
import { categoryIcon, categoryLabel, dayLabel, money, monthLabel } from "./financeLabels";

/** Listede gosterilen tek hareket -- gelir ve gider ayni sekle indirgenir. */
interface Flow extends EditableTransaction {
  sub: string | null;
}

/** Gelir/gider kayitlarini tek listeye indirger (secili ay icin). */
export function buildFlows(expenses: Expense[], incomes: Income[], month: string): Flow[] {
  const rows: Flow[] = [
    ...expenses.map((item) => ({
      id: item.id,
      title: item.title,
      amount: item.amount,
      currency: item.currency,
      category: item.category,
      day: item.spent_on,
      kind: "expense" as const,
      sub: item.sub,
    })),
    ...incomes.map((item) => ({
      id: item.id,
      title: item.title,
      amount: item.amount,
      currency: item.currency,
      category: item.category,
      day: item.received_on,
      kind: "income" as const,
      sub: null,
    })),
  ];
  return rows
    .filter((row) => row.day.startsWith(month))
    .sort((a, b) => b.day.localeCompare(a.day) || a.title.localeCompare(b.title, "tr"));
}

/** "Bugün" / "Dün" / "26 Ağustos Çarşamba" -- Apple Wallet blok basligi. */
function blockLabel(day: string): string {
  const diff = daysBetween(day, todayKey());
  if (diff === 0) return "Bugün";
  if (diff === 1) return "Dün";
  return dayLabel(day);
}

const FILTERS = [
  { id: "all", label: "Tümü" },
  { id: "expense", label: "Harcamalar" },
  { id: "income", label: "Gelirler" },
] as const;
type Filter = (typeof FILTERS)[number]["id"];

/**
 * Hareketler: gun bloklu kartlar + arama + tur filtresi.
 *
 * Satir ici duzenleme formu kaldirildi -- bir satira tiklamak duzenleme
 * modalini acar, liste hep ayni ritimde kalir.
 */
export function FinanceTransactionsTab({ flows, month, online }: { flows: Flow[]; month: string; online: boolean }) {
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Flow | null>(null);

  const visible = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase("tr");
    return flows.filter((row) => {
      if (filter !== "all" && row.kind !== filter) return false;
      if (!needle) return true;
      return (
        row.title.toLocaleLowerCase("tr").includes(needle) ||
        categoryLabel(row.category).toLocaleLowerCase("tr").includes(needle) ||
        String(row.amount).includes(needle)
      );
    });
  }, [flows, filter, search]);

  const days = useMemo(() => [...new Set(visible.map((row) => row.day))], [visible]);

  /** Gun blokunun net toplami: gelir eksi gider (isaretli). */
  function dayNet(rows: Flow[], currency: string): string {
    const total = rows.reduce(
      (sum, row) => sum + (row.kind === "income" ? Number(row.amount) : -Number(row.amount)),
      0,
    );
    const sign = total > 0 ? "+" : total < 0 ? "−" : "";
    return `${sign}${money(Math.abs(total), currency, 0)}`;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {FILTERS.map((item) => (
          <FilterChip key={item.id} label={item.label} active={filter === item.id} onClick={() => setFilter(item.id)} />
        ))}
        <div className="relative min-w-[12rem] flex-1">
          <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-icon" />
          <Input
            value={search}
            onChange={setSearch}
            placeholder="Migros, Kira…"
            ariaLabel="Hareketlerde ara"
            className="pl-8"
          />
        </div>
        <span className="text-meta text-muted">{visible.length} kayıt</span>
      </div>

      {visible.length === 0 ? (
        <Empty variant="page" title="Kayıt yok">
          {monthLabel(month)} ayında bu filtreye uyan hareket yok.
        </Empty>
      ) : (
        days.map((dayKey) => {
          const rows = visible.filter((row) => row.day === dayKey);
          return (
            <Section
              key={dayKey}
              title={blockLabel(dayKey)}
              hint={<span className="numeral tabular-nums">{dayNet(rows, rows[0]?.currency ?? "TRY")}</span>}
            >
              <RowList>
                {rows.map((row) => {
                  const Icon = categoryIcon(row.category);
                  const income = row.kind === "income";
                  return (
                    <button
                      key={row.id}
                      type="button"
                      onClick={() => setEditing(row)}
                      aria-label={`${row.title} hareketini düzenle`}
                      className="flex w-full items-center gap-3 rounded-control px-1 py-2.5 text-left text-body transition hover:bg-surface-hover"
                    >
                      <span
                        aria-hidden
                        className={cx(
                          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border",
                          income
                            ? "border-ok-border bg-ok-surface text-ok"
                            : "border-subtle bg-surface-sunken text-secondary",
                        )}
                      >
                        <Icon size={15} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-primary">{row.title}</span>
                        <span className="mt-0.5 flex items-center gap-1.5">
                          <Chip tone={income ? "ok" : "neutral"}>{categoryLabel(row.category)}</Chip>
                          {row.day !== todayKey() && <span className="text-micro text-muted">{row.day}</span>}
                        </span>
                      </span>
                      <strong
                        className={cx(
                          "numeral shrink-0 tabular-nums font-semibold",
                          income ? "text-ok" : "text-primary",
                        )}
                      >
                        {income ? "+" : "−"}
                        {money(row.amount, row.currency)}
                      </strong>
                    </button>
                  );
                })}
              </RowList>
            </Section>
          );
        })
      )}

      <EditTransactionDialog transaction={editing} onClose={() => setEditing(null)} online={online} />
    </div>
  );
}
