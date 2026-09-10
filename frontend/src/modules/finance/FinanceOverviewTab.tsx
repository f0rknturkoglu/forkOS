import { useState } from "react";
import { Check, Pencil, TrendingDown, TrendingUp } from "lucide-react";
import type { CurrencyOverview, RecurringPayment } from "@/core/types";
import { Button, Chip, Empty, Field, IconButton, NumberInput, RowList, Section, cx } from "@/core/ui";
import { daysBetween, todayKey } from "@/lib/date";
import { categoryIcon, categoryLabel, colorOf, dueLabel, money, monthShort, percent } from "./financeLabels";
import { SubBadge } from "./SubBadge";

/** `/finance/summary` tek satiri: bir ayin toplam gelir/gideri. */
export interface MonthlySummary {
  month: string;
  income: number;
  expense: number;
}

function daysLeftInMonth(): number {
  const [year, month] = todayKey().split("-").map(Number);
  const last = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return Math.max(
    0,
    daysBetween(todayKey(), `${year}-${String(month).padStart(2, "0")}-${String(last).padStart(2, "0")}`),
  );
}

/**
 * Segmentli harcama cubugu: cok katmanli halka yerine TEK yatay bar.
 * Her kategori kendi tema tokeni rengini alir; altinda yuzdesi yazar.
 */
function SpendBar({ row }: { row: CurrencyOverview }) {
  const parts = [...row.expense_by_category]
    .filter((item) => Number(item.amount) > 0)
    .sort((a, b) => Number(b.amount) - Number(a.amount));
  const total = parts.reduce((sum, item) => sum + Number(item.amount), 0);
  if (total <= 0) return <Empty>Bu ay gider yok.</Empty>;

  return (
    <div className="space-y-3">
      <div
        className="flex h-3 w-full overflow-hidden rounded-control bg-surface-sunken"
        role="img"
        aria-label="Kategoriye göre harcama dağılımı"
      >
        {parts.map((item, index) => (
          <span
            key={item.category}
            title={`${categoryLabel(item.category)} · ${money(item.amount, row.currency, 0)} (${percent(Number(item.amount) / total)})`}
            style={{ width: `${(Number(item.amount) / total) * 100}%`, background: colorOf(index) }}
          />
        ))}
      </div>
      <ul className="grid gap-x-4 gap-y-1.5 sm:grid-cols-2">
        {parts.map((item, index) => {
          const Icon = categoryIcon(item.category);
          return (
            <li key={item.category} className="flex items-center gap-2 text-meta">
              <span aria-hidden className="h-2 w-2 shrink-0 rounded-full" style={{ background: colorOf(index) }} />
              <Icon size={13} className="shrink-0 text-icon" />
              <span className="min-w-0 flex-1 truncate text-secondary">{categoryLabel(item.category)}</span>
              <span className="numeral shrink-0 tabular-nums text-muted">{percent(Number(item.amount) / total)}</span>
              <span className="numeral shrink-0 tabular-nums text-primary">{money(item.amount, row.currency, 0)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/**
 * Ozet: tek buyuk bakiye karti, tek harcama cubugu ve tek cumlelik icgoru.
 *
 * Onceden dort grafik ust uste yigiliyordu (halka + oran barı + kategori
 * barlari + aylik grafik) ve ekran "muhasebe tablosu" gibi okunuyordu.
 */
export function FinanceOverviewTab({
  row,
  summary,
  recurring,
  budget,
  onBudget,
  online,
}: {
  row: CurrencyOverview;
  summary: MonthlySummary[];
  recurring: RecurringPayment[];
  /** Secili para biriminin aylik tavani; tanimsizsa butce yok. */
  budget: number | null;
  onBudget: (value: number | null) => void;
  online: boolean;
}) {
  const [draft, setDraft] = useState<number | null>(null);
  const [editing, setEditing] = useState(false);

  const income = Number(row.income);
  const expense = Number(row.expense);
  const net = Number(row.net);
  const target = budget ?? income;
  const used = target > 0 ? Math.min(1, expense / target) : 0;
  const left = target - expense;

  const top = [...row.expense_by_category].sort((a, b) => Number(b.amount) - Number(a.amount))[0];
  const current = summary[summary.length - 1];
  const previous = summary[summary.length - 2];
  const delta =
    current && previous && previous.expense > 0 ? (current.expense - previous.expense) / previous.expense : null;

  const upcoming = recurring
    .filter((item) => item.active && item.next_due_at)
    .sort((a, b) => (a.next_due_at ?? "").localeCompare(b.next_due_at ?? ""))
    .slice(0, 5);

  return (
    <div className="space-y-5">
      <Section title="Bakiye" bodyClassName="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-meta text-muted">{budget ? "Kalan bütçe" : "Net durum"}</p>
            <p className={cx("numeral text-title", left < 0 ? "text-danger" : "text-primary")}>
              {money(left, row.currency, 0)}
            </p>
          </div>
          <div className="flex items-center gap-2 text-meta text-muted">
            {budget ? (
              <>
                <span className="numeral tabular-nums">
                  {percent(used)} harcandı · ayın bitmesine {daysLeftInMonth()} gün
                </span>
                <IconButton
                  title="Bütçeyi düzenle"
                  onClick={() => {
                    setDraft(budget);
                    setEditing(true);
                  }}
                  className="h-6 w-6"
                >
                  <Pencil size={13} />
                </IconButton>
              </>
            ) : (
              <button type="button" onClick={() => setEditing(true)} className="text-accent transition hover:underline">
                Aylık bütçe belirle
              </button>
            )}
          </div>
        </div>

        <div className="h-2.5 overflow-hidden rounded-control bg-surface-sunken">
          <div
            className={cx(
              "h-full rounded-control transition-all",
              used > 0.9 ? "bg-danger" : used > 0.75 ? "bg-warn" : "bg-ok",
            )}
            style={{ width: `${used * 100}%` }}
          />
        </div>

        {editing && (
          <div className="flex flex-wrap items-end gap-2 border-t border-subtle pt-3">
            <Field label={`Aylık bütçe (${row.currency})`}>
              <NumberInput
                value={draft === null ? NaN : draft}
                onChange={(next) => setDraft(Number.isFinite(next) ? next : null)}
                min={0}
                step={100}
                placeholder="30000"
                ariaLabel="Aylık bütçe"
                className="w-40"
              />
            </Field>
            <Button
              variant="primary"
              disabled={!online}
              onClick={() => {
                onBudget(draft && draft > 0 ? draft : null);
                setEditing(false);
              }}
            >
              <Check size={13} /> Kaydet
            </Button>
          </div>
        )}

        <div className="grid grid-cols-3 gap-3 border-t border-subtle pt-3 text-meta">
          <div>
            <p className="text-muted">Gelir</p>
            <p className="numeral tabular-nums text-ok">+{money(income, row.currency, 0)}</p>
          </div>
          <div>
            <p className="text-muted">Harcama</p>
            <p className="numeral tabular-nums text-danger">−{money(expense, row.currency, 0)}</p>
          </div>
          <div>
            <p className="text-muted">Sabit faturalar</p>
            <p className="numeral tabular-nums text-primary">
              {money(row.recurring_monthly, row.currency, 0)}
              <span className="text-meta text-muted">/ay</span>
            </p>
          </div>
        </div>
      </Section>

      <Section title="Bu ay nereye gitti" hint="kategori payı">
        <SpendBar row={row} />
      </Section>

      {top && (
        <div className="flex items-start gap-2 rounded-card border border-subtle bg-surface-sunken px-3.5 py-3">
          {delta !== null && delta <= 0 ? (
            <TrendingDown size={15} className="mt-0.5 shrink-0 text-ok" />
          ) : (
            <TrendingUp size={15} className="mt-0.5 shrink-0 text-warn" />
          )}
          <p className="text-body text-secondary">
            Bu ay en büyük harcama kalemin{" "}
            <strong className="font-medium text-primary">{categoryLabel(top.category)}</strong>
            {` (${money(top.amount, row.currency, 0)})`}
            {delta !== null
              ? `. Geçen aya göre harcamaların ${percent(Math.abs(delta))} daha ${delta <= 0 ? "az" : "fazla"}.`
              : ". Geçen ay verisi yok."}
            {budget ? ` Bütçenin ${percent(used)} kadarı kullanıldı.` : ""}
          </p>
        </div>
      )}

      {summary.length >= 2 && (
        <p className="px-1 text-meta text-muted">
          Son 6 ay:{" "}
          {summary.map((point) => `${monthShort(point.month)} ${money(point.expense, row.currency, 0)}`).join(" · ")}
        </p>
      )}

      <Section title="Yaklaşan ödemeler" hint={upcoming.length > 0 ? `${upcoming.length} abonelik` : undefined}>
        {upcoming.length === 0 ? (
          <Empty>Planlanmış abonelik ödemesi yok.</Empty>
        ) : (
          <RowList>
            {upcoming.map((item) => {
              const days = daysBetween(todayKey(), item.next_due_at ?? todayKey());
              return (
                <div key={item.id} className="flex items-center gap-3 py-2.5 text-body">
                  <SubBadge sub={item.sub} title={item.title} size={20} />
                  <span className="min-w-0 flex-1 truncate">{item.title}</span>
                  <Chip tone={days < 0 ? "danger" : days <= 3 ? "warn" : "neutral"}>{dueLabel(days)}</Chip>
                  <strong className="numeral shrink-0 tabular-nums">{money(item.amount, item.currency)}</strong>
                </div>
              );
            })}
          </RowList>
        )}
      </Section>
    </div>
  );
}
