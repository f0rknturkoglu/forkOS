import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Check, Pencil, Plus, Trash2 } from "lucide-react";
import { api, qs } from "@/core/api";
import { navigate, useHashRoute } from "@/app/router";
import { invalidateAfter } from "@/core/invalidation";
import { RelatedPanel } from "@/core/RelatedPanel";
import type { CurrencyOverview, Expense, FinanceOverview, Income, RecurringPayment } from "@/core/types";
import {
  Button,
  Chip,
  cx,
  Empty,
  Field,
  IconButton,
  Input,
  Metric,
  MetricStrip,
  NumberInput,
  PageFrame,
  PageHeader,
  RowList,
  Section,
  Select,
  Toolbar,
  useToast,
} from "@/core/ui";
import { daysBetween, todayKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import {
  billingLabel,
  categoryLabel,
  colorOf,
  dayLabel,
  dueLabel,
  EXPENSE_CATEGORIES,
  FREQUENCIES,
  frequencyLabel,
  INCOME_CATEGORIES,
  money,
  moneyShort,
  monthKeyOf,
  monthLabel,
  monthShort,
  percent,
  parseMonth,
  shiftMonth,
  signedMoney,
  subColor,
  subSlug,
} from "./financeLabels";

type Tab = "summary" | "flow" | "subs";
const TABS: { id: Tab; label: string }[] = [
  { id: "summary", label: "Özet" },
  { id: "flow", label: "Hareketler" },
  { id: "subs", label: "Abonelikler" },
];

/** Listede gosterilen tek hareket -- gelir ve gider ayni sekle indirgenir. */
interface Flow {
  id: string;
  title: string;
  amount: string;
  currency: string;
  category: string;
  day: string;
  kind: "income" | "expense";
  sub: string | null;
}

/* ══ Kucuk parcalar ══════════════════════════════════════════════════ */

/** Abonelik rozeti: adin bas harfi, marka rengiyle. */
function SubBadge({ sub, title, size = 24 }: { sub: string | null; title: string; size?: number }) {
  const letter = (title.trim()[0] ?? "?").toLocaleUpperCase("tr");
  return (
    <span
      aria-hidden
      className="flex shrink-0 select-none items-center justify-center rounded-full font-medium text-canvas"
      style={{ background: subColor(sub), width: size, height: size, fontSize: size * 0.46 }}
    >
      {letter}
    </span>
  );
}

/** Gelir/gider oranini tek bakista veren yatay cubuk. */
function FlowBar({ income, expense, currency }: { income: number; expense: number; currency: string }) {
  const peak = Math.max(income, expense, 1);
  const rows = [
    { label: "Gelir", value: income, tone: "bg-ok", text: "text-ok" },
    { label: "Gider", value: expense, tone: "bg-danger", text: "text-danger" },
  ];
  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <div key={row.label}>
          <div className="mb-1 flex items-baseline justify-between gap-3 text-meta">
            <span className="text-secondary">{row.label}</span>
            <span className={"numeral font-medium " + row.text}>{money(row.value, currency, 0)}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-control bg-surface-sunken">
            <div className={"h-full rounded-control " + row.tone} style={{ width: `${(row.value / peak) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

const RADIUS = 48;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
/** Dilim uzerindeyken kalinlasir -- banka uygulamalarindaki "one cikma". */
const RING = { rest: 14, active: 19 };
const SLICE_MOTION = { transition: "stroke-width 120ms ease, opacity 120ms ease" };

/**
 * Ortada duran kategori halkasi.
 *
 * Merkez bos degil: fare hicbir dilimin uzerinde degilken ayin ozetini
 * (gider, gelir, abonelik) yazar; bir dilime gelince o kategorinin tutari ve
 * payi gecer. Legend ile halka ayni "active" durumunu paylasir, iki taraftan
 * da gezilebilir.
 */
function SpendDonut({ row }: { row: CurrencyOverview }) {
  const [active, setActive] = useState<number | null>(null);
  const segments = row.expense_by_category.map((entry, index) => ({
    label: categoryLabel(entry.category),
    value: Number(entry.amount),
    color: colorOf(index),
  }));
  const total = segments.reduce((sum, segment) => sum + segment.value, 0);
  const hovered = active === null ? undefined : segments[active];
  let offset = 0;

  return (
    <div className="flex flex-col items-center gap-5">
      <div className="relative h-64 w-64 shrink-0">
        <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
          <circle cx="60" cy="60" r={RADIUS} fill="none" stroke="var(--surface-sunken)" strokeWidth={RING.rest} />
          {segments.map((segment, index) => {
            const fraction = segment.value / (total || 1);
            const dash = fraction * CIRCUMFERENCE;
            const slice = (
              <circle
                key={segment.label}
                cx="60"
                cy="60"
                r={RADIUS}
                fill="none"
                stroke={segment.color}
                strokeWidth={active === index ? RING.active : RING.rest}
                strokeDasharray={`${dash} ${CIRCUMFERENCE - dash}`}
                strokeDashoffset={-offset * CIRCUMFERENCE}
                opacity={active === null || active === index ? 1 : 0.3}
                className="cursor-pointer"
                style={SLICE_MOTION}
                onMouseEnter={() => setActive(index)}
                onMouseLeave={() => setActive(null)}
              >
                <title>{`${segment.label} · ${money(segment.value, row.currency, 0)}`}</title>
              </circle>
            );
            offset += fraction;
            return slice;
          })}
        </svg>

        {/* Halkanin gobegi. pointer-events-none: dilimlerin hedefini kapatmasin. */}
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-10 text-center">
          {hovered ? (
            <>
              <span className="numeral text-numeral-xl text-primary">{money(hovered.value, row.currency, 0)}</span>
              <span className="mt-0.5 truncate text-body text-secondary">{hovered.label}</span>
              <span className="numeral text-meta text-muted">{percent(hovered.value / (total || 1))}</span>
            </>
          ) : (
            <>
              <span className="numeral text-numeral-xl text-primary">{moneyShort(row.expense, row.currency)}</span>
              <span className="mt-0.5 text-body text-secondary">Gider</span>
              <span className="numeral mt-2 text-meta text-ok">Gelir {moneyShort(row.income, row.currency)}</span>
              <span className="numeral text-meta text-muted">
                Abonelik {moneyShort(row.recurring_monthly, row.currency)}/ay
              </span>
            </>
          )}
        </div>
      </div>

      <div className="flex flex-wrap justify-center gap-x-4 gap-y-1.5">
        {segments.map((segment, index) => (
          <button
            key={segment.label}
            type="button"
            onMouseEnter={() => setActive(index)}
            onMouseLeave={() => setActive(null)}
            onFocus={() => setActive(index)}
            onBlur={() => setActive(null)}
            className={cx(
              "flex items-center gap-1.5 rounded-control px-1.5 py-0.5 text-meta transition",
              active === index ? "bg-surface-hover text-primary" : "text-secondary",
            )}
          >
            <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: segment.color }} />
            {segment.label}
            <span className="numeral text-muted">{money(segment.value, row.currency, 0)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ══ Grafik + hizli ekleme ═══════════════════════════════════════════ */

/** GET /finance/summary tek satiri: bir ayin toplam gelir/gideri. */
interface MonthlySummary {
  month: string;
  income: number;
  expense: number;
}

/** Ozet karti trend oku: bu ay vs gecen ay. `invert` ile artis "kotu" (gider). */
function TrendDelta({ ratio, invert = false }: { ratio: number | null; invert?: boolean }) {
  if (ratio === null || ratio === 0) return null;
  const up = ratio > 0;
  const good = invert ? !up : up;
  return (
    <span className={good ? "text-ok" : "text-danger"}>
      {up ? "▲" : "▼"} %{Math.round(Math.abs(ratio) * 100)} vs geçen ay
    </span>
  );
}

/** Sayfa ustunde hizli gider: tutar + kategori + not; Enter ile kaydeder. */
function QuickAddForm({ online, onRefresh }: { online: boolean; onRefresh: () => void }) {
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("food");
  const [note, setNote] = useState("");
  const create = useMutation({
    mutationFn: () => {
      const text = note.trim();
      return api.post("/expenses", {
        // Not girilmemisse kategori adi baslik olur; liste bos baslik gostermez.
        title: text || categoryLabel(category),
        amount,
        category,
        note: text || null,
        spent_on: todayKey(),
      });
    },
    onSuccess: () => {
      setAmount("");
      setNote("");
      onRefresh();
    },
  });
  const toast = useToast();
  const valid = Number(amount) > 0;
  return (
    <Section title="Hızlı gider ekle" hint="Enter ile kaydet · bugünün tarihine işlenir">
      <form
        className="grid items-end gap-3 md:grid-cols-[9rem_10rem_1fr_auto]"
        onSubmit={(e) => {
          e.preventDefault();
          if (!valid) {
            toast.push("Lütfen geçerli bir tutar girin.", { tone: "warn" });
            return;
          }
          if (online) create.mutate();
        }}
      >
        <Field label="Tutar">
          <NumberInput
            value={amount === "" ? NaN : Number(amount)}
            onChange={(next) => setAmount(String(next))}
            placeholder="0,00"
            min={0}
            step={0.01}
            className="w-full"
          />
        </Field>
        <Field label="Kategori">
          <Select value={category} onChange={setCategory} className="w-full">
            {EXPENSE_CATEGORIES.map((item) => (
              <option key={item} value={item}>
                {categoryLabel(item)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Not">
          <Input value={note} onChange={setNote} placeholder="Ne harcadın? (başlık olur)" className="w-full" />
        </Field>
        <Button type="submit" variant="primary" disabled={!online || create.isPending || !valid}>
          <Plus size={14} /> Ekle
        </Button>
      </form>
    </Section>
  );
}

/** Son 6 ayin gelir/gider cubuk grafigi -- el yapimi SVG, tema tokenlariyla. */
function MonthlyBarChart({ summary, currency }: { summary: MonthlySummary[]; currency: string }) {
  const peak = Math.max(1, ...summary.flatMap((row) => [row.income, row.expense]));
  const W = 640;
  const H = 200;
  const padTop = 12;
  const padBottom = 26;
  const plotH = H - padTop - padBottom;
  const slot = W / summary.length;
  const barW = Math.min(20, slot * 0.26);
  const gap = 3;

  return (
    <div>
      <div className="mb-2 flex items-center gap-4 text-meta text-secondary">
        <span className="flex items-center gap-1.5">
          <span aria-hidden className="h-2.5 w-2.5 rounded-sm" style={{ background: "var(--success)" }} />
          Gelir
        </span>
        <span className="flex items-center gap-1.5">
          <span aria-hidden className="h-2.5 w-2.5 rounded-sm" style={{ background: "var(--danger)" }} />
          Gider
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Son 6 ayın gelir ve gider çubuk grafiği" className="w-full">
        {summary.map((row, index) => {
          const center = slot * index + slot / 2;
          const incomeH = (row.income / peak) * plotH;
          const expenseH = (row.expense / peak) * plotH;
          return (
            <g key={row.month}>
              <rect
                x={center - barW - gap / 2}
                y={padTop + plotH - Math.max(incomeH, 1)}
                width={barW}
                height={Math.max(incomeH, 1)}
                fill="var(--success)"
                rx={2}
              >
                <title>{`${monthLabel(row.month)} · gelir ${money(row.income, currency, 0)}`}</title>
              </rect>
              <rect
                x={center + gap / 2}
                y={padTop + plotH - Math.max(expenseH, 1)}
                width={barW}
                height={Math.max(expenseH, 1)}
                fill="var(--danger)"
                rx={2}
              >
                <title>{`${monthLabel(row.month)} · gider ${money(row.expense, currency, 0)}`}</title>
              </rect>
              <text x={center} y={H - 8} textAnchor="middle" className="text-meta" fill="var(--text-muted)">
                {monthShort(row.month)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/** Son 30 gunun giderleri: en buyuk 5 kategori + "Diger" -- yatay barlar. */
function CategoryBars({ expenses, currency }: { expenses: Expense[]; currency: string }) {
  const today = todayKey();
  const buckets = new Map<string, number>();
  for (const row of expenses) {
    const days = daysBetween(row.spent_on, today);
    if (days < 0 || days > 29) continue;
    buckets.set(row.category, (buckets.get(row.category) ?? 0) + Number(row.amount));
  }
  const sorted = [...buckets.entries()].sort((a, b) => b[1] - a[1]);
  const top = sorted.slice(0, 5);
  const rest = sorted.slice(5).reduce((sum, [, value]) => sum + value, 0);
  const rows: [string, number][] = rest > 0 ? [...top, ["other", rest]] : top;
  const total = sorted.reduce((sum, [, value]) => sum + value, 0);
  const peak = Math.max(1, ...rows.map(([, value]) => value));

  if (rows.length === 0) {
    return <Empty>Son 30 günde gider yok.</Empty>;
  }

  return (
    <div className="space-y-2.5">
      {rows.map(([category, value], index) => (
        <div key={category}>
          <div className="mb-1 flex items-baseline justify-between gap-3 text-meta">
            <span className="truncate text-secondary">{categoryLabel(category)}</span>
            <span className="numeral shrink-0 text-muted">
              {money(value, currency, 0)} · {percent(value / (total || 1))}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-control bg-surface-sunken">
            <div
              className="h-full rounded-control"
              style={{ width: `${(value / peak) * 100}%`, background: colorOf(index) }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ══ Sayfa ═══════════════════════════════════════════════════════════ */

export function FinancePage() {
  const route = useHashRoute();
  // Sekme ve ay URL'de yasar: yenileyince kaybolmaz, baglanti paylasilabilir.
  const focusId = route.params.get("focus") ?? "";
  const tab = (TABS.find((t) => t.id === route.params.get("tab"))?.id ?? "summary") as Tab;
  const month = route.params.get("month") ?? monthKeyOf(todayKey());
  const thisMonth = monthKeyOf(todayKey());
  const online = useOnline();

  const go = (next: { tab?: Tab; month?: string }) =>
    navigate("/finance" + qs({ tab: next.tab ?? tab, month: next.month ?? month, focus: focusId }));

  const { year, month: monthNumber } = parseMonth(month);
  const { data: overview } = useQuery({
    queryKey: ["finance-overview", month],
    queryFn: () => api.get<FinanceOverview>("/finance/overview" + qs({ year, month: monthNumber })),
  });
  const { data: expenses = [] } = useQuery({ queryKey: ["expenses"], queryFn: () => api.get<Expense[]>("/expenses") });
  const { data: incomes = [] } = useQuery({ queryKey: ["incomes"], queryFn: () => api.get<Income[]>("/incomes") });
  const { data: summary = [] } = useQuery({
    queryKey: ["finance-summary"],
    queryFn: () => api.get<MonthlySummary[]>("/finance/summary" + qs({ months: 6 })),
  });
  const { data: recurring = [] } = useQuery({
    queryKey: ["recurring"],
    queryFn: () => api.get<RecurringPayment[]>("/recurring-payments"),
  });

  const refresh = () => invalidateAfter("finance.write");
  const remove = useMutation({
    mutationFn: ({ id, kind }: { id: string; kind: "expenses" | "incomes" | "recurring-payments" }) =>
      api.del(`/${kind}/${id}`),
    onSuccess: refresh,
  });
  const pay = useMutation({
    mutationFn: (id: string) => api.post(`/recurring-payments/${id}/pay`),
    onSuccess: refresh,
  });

  /* Secili ayin hareketleri, gunu yeniden eskiye. */
  const flows = useMemo<Flow[]>(() => {
    const rows: Flow[] = [
      ...expenses.map((x) => ({ ...x, day: x.spent_on, kind: "expense" as const })),
      ...incomes.map((x) => ({ ...x, day: x.received_on, kind: "income" as const, sub: null })),
    ];
    return rows.filter((row) => monthKeyOf(row.day) === month).sort((a, b) => b.day.localeCompare(a.day));
  }, [expenses, incomes, month]);

  const currencies = overview?.currencies ?? [];
  const primary = currencies[0];

  /* Bu ay vs gecen ay oku -- ozet kartlarinda (summary'nin son iki satiri). */
  const trend = useMemo(() => {
    if (summary.length < 2) return null;
    const last = summary[summary.length - 1];
    const prev = summary[summary.length - 2];
    if (!last || !prev) return null;
    return {
      income: prev.income > 0 ? (last.income - prev.income) / prev.income : last.income > 0 ? 1 : 0,
      expense: prev.expense > 0 ? (last.expense - prev.expense) / prev.expense : last.expense > 0 ? 1 : 0,
    };
  }, [summary]);

  return (
    <PageFrame className="space-y-5">
      <PageHeader
        eyebrow="Takip"
        title="Finans"
        action={
          <div className="flex items-center gap-1.5">
            <IconButton title="Önceki ay" onClick={() => go({ month: shiftMonth(month, -1) })}>
              <ChevronLeft size={15} />
            </IconButton>
            <span className="w-36 text-center text-heading text-primary">{monthLabel(month)}</span>
            <IconButton title="Sonraki ay" onClick={() => go({ month: shiftMonth(month, 1) })}>
              <ChevronRight size={15} />
            </IconButton>
            {month !== thisMonth && (
              <Button size="sm" onClick={() => go({ month: thisMonth })}>
                Bu ay
              </Button>
            )}
          </div>
        }
      />

      {currencies.map((row) => (
        <MetricStrip key={row.currency} className="grid-cols-2 sm:grid-cols-4">
          <Metric
            label="Gelir"
            value={<span className="text-ok">{moneyShort(row.income, row.currency)}</span>}
            hint={trend && <TrendDelta ratio={trend.income} />}
          />
          <Metric
            label="Gider"
            value={<span className="text-danger">{moneyShort(row.expense, row.currency)}</span>}
            hint={trend && <TrendDelta ratio={trend.expense} invert />}
          />
          <Metric
            label="Net"
            value={
              <span className={Number(row.net) < 0 ? "text-danger" : "text-ok"}>
                {signedMoney(row.net, row.currency)}
              </span>
            }
            hint={Number(row.net) < 0 ? "Bu ay açık verdin" : "Bu ay artıda"}
          />
          <Metric label="Abonelik" value={moneyShort(row.recurring_monthly, row.currency)} hint="aylık sabit yük" />
        </MetricStrip>
      ))}
      <QuickAddForm online={online} onRefresh={refresh} />
      {!primary && (
        <Empty variant="page" title="Bu ay boş">
          Aşağıdaki “Hareketler” sekmesinden ilk gelir veya giderini ekle.
        </Empty>
      )}

      <Toolbar>
        {TABS.map((item) => (
          <Button key={item.id} variant={tab === item.id ? "primary" : "ghost"} onClick={() => go({ tab: item.id })}>
            {item.label}
          </Button>
        ))}
        <span className="ml-auto text-meta text-muted">Kur dönüşümü yok; her para birimi kendi toplamında kalır.</span>
      </Toolbar>

      {tab === "summary" && (
        <SummaryTab currencies={currencies} recurring={recurring} summary={summary} expenses={expenses} />
      )}
      {tab === "flow" && (
        <FlowTab
          flows={flows}
          month={month}
          online={online}
          onRefresh={refresh}
          onDelete={(id, kind) => remove.mutate({ id, kind })}
        />
      )}
      {tab === "subs" && (
        <SubsTab
          recurring={recurring}
          online={online}
          onRefresh={refresh}
          onPay={(id) => pay.mutate(id)}
          onDelete={(id) => remove.mutate({ id, kind: "recurring-payments" })}
        />
      )}

      {focusId && (
        <Section title="Bağlı kayıtlar">
          <RelatedPanel entityId={focusId} />
        </Section>
      )}
    </PageFrame>
  );
}

/* ══ Özet ════════════════════════════════════════════════════════════ */

function SummaryTab({
  currencies,
  recurring,
  summary,
  expenses,
}: {
  currencies: CurrencyOverview[];
  recurring: RecurringPayment[];
  summary: MonthlySummary[];
  expenses: Expense[];
}) {
  const upcoming = recurring
    .filter((x) => x.active && x.next_due_at)
    .sort((a, b) => (a.next_due_at ?? "").localeCompare(b.next_due_at ?? ""))
    .slice(0, 5);

  if (currencies.length === 0) return null;

  return (
    <div className="space-y-5">
      <Section title="Aylık akış" hint="Son 6 ay · gelir / gider">
        {summary.length === 0 ? (
          <Empty>Grafik için veri yok.</Empty>
        ) : (
          <div className="py-1">
            <MonthlyBarChart summary={summary} currency={currencies[0].currency} />
          </div>
        )}
      </Section>
      <Section title="Son 30 gün · kategori dağılımı" hint="En büyük 5 + Diğer">
        <CategoryBars expenses={expenses} currency={currencies[0].currency} />
      </Section>
      {currencies.map((row) => (
        <div key={row.currency} className="space-y-5">
          {/* Halka sayfanin merkezinde ve tek basina -- ozetin ana gorseli. */}
          <Section title={`Gider dağılımı · ${row.currency.trim()}`} hint="Dilimin üzerine gel">
            {row.expense_by_category.length === 0 ? (
              <Empty>Bu ay gider yok.</Empty>
            ) : (
              <div className="py-2">
                <SpendDonut row={row} />
              </div>
            )}
          </Section>
          <Section title="Gelir / gider">
            <FlowBar income={Number(row.income)} expense={Number(row.expense)} currency={row.currency} />
            <p className="mt-4 border-t border-subtle pt-3 text-meta text-secondary">
              {Number(row.net) < 0
                ? `Giderin gelirini ${money(Math.abs(Number(row.net)), row.currency, 0)} aştı.`
                : `Bu ay ${money(Number(row.net), row.currency, 0)} biriktirdin.`}
            </p>
          </Section>
        </div>
      ))}

      <Section title="Yaklaşan ödemeler">
        {upcoming.length === 0 ? (
          <Empty>Planlanmış abonelik ödemesi yok.</Empty>
        ) : (
          <RowList>
            {upcoming.map((item) => (
              <div key={item.id} className="flex items-center gap-3 py-2.5 text-body">
                <SubBadge sub={item.sub} title={item.title} size={20} />
                <span className="min-w-0 flex-1 truncate">{item.title}</span>
                <span className="shrink-0 text-meta text-muted">
                  {dueLabel(daysBetween(todayKey(), item.next_due_at ?? todayKey()))}
                </span>
                <strong className="numeral shrink-0">{money(item.amount, item.currency)}</strong>
              </div>
            ))}
          </RowList>
        )}
      </Section>
    </div>
  );
}

/* ══ Hareketler ══════════════════════════════════════════════════════ */

function FlowTab({
  flows,
  month,
  online,
  onRefresh,
  onDelete,
}: {
  flows: Flow[];
  month: string;
  online: boolean;
  onRefresh: () => void;
  onDelete: (id: string, kind: "expenses" | "incomes") => void;
}) {
  const [kind, setKind] = useState<"expense" | "income">("expense");
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("food");
  const [day, setDay] = useState(todayKey());
  const [filter, setFilter] = useState<"all" | "income" | "expense">("all");
  // Satir ici duzeltme: yanlis girilen tutari silip yeniden yazmak gerekmesin.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editAmount, setEditAmount] = useState("");

  const categories = kind === "expense" ? EXPENSE_CATEGORIES : INCOME_CATEGORIES;
  const create = useMutation({
    mutationFn: () =>
      kind === "expense"
        ? api.post("/expenses", { title, amount, category, spent_on: day })
        : api.post("/incomes", { title, amount, category, received_on: day }),
    onSuccess: () => {
      setTitle("");
      setAmount("");
      onRefresh();
    },
  });

  const update = useMutation({
    mutationFn: ({ id, kind: rowKind }: { id: string; kind: "expenses" | "incomes" }) => {
      const body = { title: editTitle, amount: editAmount };
      return rowKind === "incomes" ? api.patch(`/incomes/${id}`, body) : api.patch(`/expenses/${id}`, body);
    },
    onSuccess: () => {
      setEditingId(null);
      onRefresh();
    },
  });

  const startEdit = (row: Flow) => {
    setEditingId(row.id);
    setEditTitle(row.title);
    setEditAmount(row.amount);
  };

  /** Tur degisince kategori o turun listesine duser -- gecersiz eslesme kalmaz. */
  const switchKind = (next: "expense" | "income") => {
    setKind(next);
    setCategory(next === "expense" ? "food" : "salary");
  };

  const toast = useToast();
  const visible = flows.filter((row) => filter === "all" || row.kind === filter);
  const days = [...new Set(visible.map((row) => row.day))];

  return (
    <div className="space-y-5">
      <Section title={kind === "expense" ? "Gider ekle" : "Gelir ekle"}>
        <div className="mb-3 flex gap-1.5">
          <Button variant={kind === "expense" ? "primary" : "ghost"} onClick={() => switchKind("expense")}>
            Gider
          </Button>
          <Button variant={kind === "income" ? "primary" : "ghost"} onClick={() => switchKind("income")}>
            Gelir
          </Button>
        </div>
        <form
          className="grid items-end gap-3 md:grid-cols-[1fr_9rem_10rem_10rem_auto]"
          onSubmit={(e) => {
            e.preventDefault();
            if (!title.trim() || !amount || Number(amount) <= 0 || isNaN(Number(amount))) {
              toast.push("Lütfen bir açıklama ve geçerli bir tutar girin.", { tone: "warn" });
              return;
            }
            create.mutate();
          }}
        >
          <Field label="Ne için">
            <Input
              value={title}
              onChange={setTitle}
              placeholder={kind === "expense" ? "Market alışverişi" : "Ağustos maaşı"}
              className="w-full"
            />
          </Field>
          <Field label="Tutar">
            <NumberInput
              value={amount === "" ? NaN : Number(amount)}
              onChange={(next) => setAmount(String(next))}
              placeholder="0,00"
              min={0}
              step={0.01}
              className="w-full"
            />
          </Field>
          <Field label="Kategori">
            <Select value={category} onChange={setCategory} className="w-full">
              {categories.map((item) => (
                <option key={item} value={item}>
                  {categoryLabel(item)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Tarih">
            <Input type="date" value={day} onChange={setDay} className="w-full" />
          </Field>
          <Button type="submit" variant="primary" disabled={!online || create.isPending}>
            <Plus size={14} /> Ekle
          </Button>
        </form>
      </Section>

      <Toolbar>
        {(["all", "income", "expense"] as const).map((item) => (
          <Button key={item} size="sm" variant={filter === item ? "primary" : "ghost"} onClick={() => setFilter(item)}>
            {item === "all" ? "Tümü" : item === "income" ? "Gelir" : "Gider"}
          </Button>
        ))}
        <span className="ml-auto text-meta text-muted">{visible.length} kayıt</span>
      </Toolbar>

      {visible.length === 0 ? (
        <Empty variant="page" title="Kayıt yok">
          {monthLabel(month)} ayında bu filtreye uyan hareket yok. Yukarıdan ekleyebilirsin.
        </Empty>
      ) : (
        days.map((dayKey) => (
          <Section key={dayKey} title={dayLabel(dayKey)}>
            <RowList>
              {visible
                .filter((row) => row.day === dayKey)
                .map((row) => (
                  <div key={row.id} className="flex items-center gap-3 py-2.5 text-body">
                    {row.sub ? (
                      <SubBadge sub={row.sub} title={row.title} size={20} />
                    ) : (
                      <span
                        aria-hidden
                        className={"h-2 w-2 shrink-0 rounded-full " + (row.kind === "income" ? "bg-ok" : "bg-danger")}
                      />
                    )}
                    {editingId === row.id ? (
                      <>
                        <Input
                          value={editTitle}
                          onChange={setEditTitle}
                          ariaLabel="Başlık"
                          className="min-w-0 flex-1"
                        />
                        <NumberInput
                          value={editAmount === "" ? NaN : Number(editAmount)}
                          onChange={(next) => setEditAmount(String(next))}
                          ariaLabel="Tutar"
                          min={0}
                          step={0.01}
                          className="w-28 shrink-0"
                        />
                        <Button
                          size="sm"
                          variant="primary"
                          disabled={!online || !editTitle.trim() || Number(editAmount) <= 0}
                          onClick={() =>
                            update.mutate({ id: row.id, kind: row.kind === "income" ? "incomes" : "expenses" })
                          }
                        >
                          Kaydet
                        </Button>
                        <Button size="sm" onClick={() => setEditingId(null)}>
                          Vazgeç
                        </Button>
                      </>
                    ) : (
                      <>
                        <span className="min-w-0 flex-1 truncate">{row.title}</span>
                        <Chip tone={row.kind === "income" ? "ok" : "neutral"}>{categoryLabel(row.category)}</Chip>
                        <strong className={"numeral shrink-0 " + (row.kind === "income" ? "text-ok" : "text-primary")}>
                          {row.kind === "income" ? "+" : "−"}
                          {money(row.amount, row.currency)}
                        </strong>
                        <IconButton title="Düzelt" disabled={!online} onClick={() => startEdit(row)}>
                          <Pencil size={14} />
                        </IconButton>
                        <IconButton
                          title="Sil"
                          tone="danger"
                          disabled={!online}
                          onClick={() => onDelete(row.id, row.kind === "income" ? "incomes" : "expenses")}
                        >
                          <Trash2 size={14} />
                        </IconButton>
                      </>
                    )}
                  </div>
                ))}
            </RowList>
          </Section>
        ))
      )}
    </div>
  );
}

/* ══ Abonelikler ═════════════════════════════════════════════════════ */

function SubsTab({
  recurring,
  online,
  onRefresh,
  onPay,
  onDelete,
}: {
  recurring: RecurringPayment[];
  online: boolean;
  onRefresh: () => void;
  onPay: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [frequency, setFrequency] = useState("monthly");
  const [billingDay, setBillingDay] = useState(1);

  /* Sonraki vade: bu ayin odeme gunu gectiyse gelecek ay. */
  const nextDue = (day: number): string => {
    const today = todayKey();
    const [year, month] = today.split("-").map(Number);
    const inMonth = Math.min(day, new Date(Date.UTC(year, month, 0)).getUTCDate());
    const candidate = `${year}-${String(month).padStart(2, "0")}-${String(inMonth).padStart(2, "0")}`;
    if (candidate >= today) return candidate;
    const nextMonth = month === 12 ? 1 : month + 1;
    const nextYear = month === 12 ? year + 1 : year;
    const clamped = Math.min(day, new Date(Date.UTC(nextYear, nextMonth, 0)).getUTCDate());
    return `${nextYear}-${String(nextMonth).padStart(2, "0")}-${String(clamped).padStart(2, "0")}`;
  };

  const create = useMutation({
    mutationFn: () =>
      api.post("/recurring-payments", {
        title,
        amount,
        category: "subscriptions",
        frequency,
        billing_day: billingDay,
        next_due_at: nextDue(billingDay),
        // Marka slug'i addan turetilir -- kullaniciya marka sectirilmez.
        sub: subSlug(title),
      }),
    onSuccess: () => {
      setTitle("");
      setAmount("");
      onRefresh();
    },
  });

  const toast = useToast();
  const active = recurring.filter((x) => x.active);
  const passive = recurring.filter((x) => !x.active);

  return (
    <div className="space-y-5">
      <Section title="Abonelik ekle" hint="Adı yaz, tutarı gir, ödeme gününü seç. Rozeti kendisi alır.">
        <form
          className="grid items-end gap-3 md:grid-cols-[1fr_9rem_9rem_9rem_auto]"
          onSubmit={(e) => {
            e.preventDefault();
            if (!title.trim() || !amount || Number(amount) <= 0 || isNaN(Number(amount))) {
              toast.push("Lütfen abonelik adı ve geçerli bir tutar girin.", { tone: "warn" });
              return;
            }
            create.mutate();
          }}
        >
          <Field label="Abonelik">
            <Input value={title} onChange={setTitle} placeholder="Netflix" className="w-full" />
          </Field>
          <Field label="Tutar">
            <NumberInput
              value={amount === "" ? NaN : Number(amount)}
              onChange={(next) => setAmount(String(next))}
              placeholder="0,00"
              min={0}
              step={0.01}
              className="w-full"
            />
          </Field>
          <Field label="Sıklık">
            <Select value={frequency} onChange={setFrequency} className="w-full">
              {FREQUENCIES.map((item) => (
                <option key={item} value={item}>
                  {frequencyLabel(item)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Ödeme günü">
            <NumberInput value={billingDay} onChange={setBillingDay} min={1} max={31} step={1} className="w-full" />
          </Field>
          <Button type="submit" variant="primary" disabled={!online || create.isPending}>
            <Plus size={14} /> Ekle
          </Button>
        </form>
      </Section>

      {active.length === 0 ? (
        <Empty variant="page" title="Abonelik yok">
          Netflix, Spotify, iCloud… Yukarıdan ekle; her ay ne kadar sabit gider taşıdığını üstteki şeritte gör.
        </Empty>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {active.map((item) => (
            <div
              key={item.id}
              className="flex flex-col gap-3 rounded-card border border-subtle bg-surface p-4 shadow-card"
            >
              <div className="flex items-start gap-2.5">
                <SubBadge sub={item.sub} title={item.title} size={28} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-heading text-primary">{item.title}</p>
                  <p className="text-meta text-muted">{billingLabel(item.frequency, item.billing_day)}</p>
                </div>
                <IconButton title="Sil" tone="danger" disabled={!online} onClick={() => onDelete(item.id)}>
                  <Trash2 size={14} />
                </IconButton>
              </div>
              <div className="flex items-baseline justify-between gap-2">
                <strong className="numeral text-numeral-lg text-primary">{money(item.amount, item.currency)}</strong>
                {item.next_due_at && (
                  <Chip tone={daysBetween(todayKey(), item.next_due_at) < 0 ? "danger" : "neutral"}>
                    {dueLabel(daysBetween(todayKey(), item.next_due_at))}
                  </Chip>
                )}
              </div>
              <Button variant="primary" disabled={!online} onClick={() => onPay(item.id)} className="w-full">
                <Check size={14} /> Ödendi olarak işaretle
              </Button>
            </div>
          ))}
        </div>
      )}

      {passive.length > 0 && (
        <Section title="Duraklatılmış">
          <RowList>
            {passive.map((item) => (
              <div key={item.id} className="flex items-center gap-3 py-2.5 text-body text-secondary">
                <SubBadge sub={item.sub} title={item.title} size={20} />
                <span className="min-w-0 flex-1 truncate">{item.title}</span>
                <span className="numeral shrink-0">{money(item.amount, item.currency)}</span>
                <IconButton title="Sil" tone="danger" disabled={!online} onClick={() => onDelete(item.id)}>
                  <Trash2 size={14} />
                </IconButton>
              </div>
            ))}
          </RowList>
        </Section>
      )}
    </div>
  );
}
