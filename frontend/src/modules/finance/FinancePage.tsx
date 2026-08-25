import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { api } from "@/core/api";
import type { Expense, RecurringPayment } from "@/core/types";
import { Badge, Button, Empty, IconButton, Metric, MetricStrip, PageFrame, PageHeader, RowList, Section, Toolbar } from "@/core/ui";
import { localDateKey } from "@/lib/date";
import { useInvalidate, useOnline } from "@/lib/hooks";

type Summary = { currency: string; category: string; amount: string };
const categories = ["food", "subscriptions", "transport", "education", "entertainment", "other"];

/* Abonelik markalari (ilk paket): WOW, YouTube, Spotify, Amazon Prime, iCloud+ */
const SUBS = [
  { id: "wow", label: "WOW", color: "#6C4CFF", letter: "W" },
  { id: "youtube", label: "YouTube", color: "#FF4E45", letter: "Y" },
  { id: "spotify", label: "Spotify", color: "#1DB954", letter: "S" },
  { id: "amazon_prime", label: "Amazon Prime", color: "#F97316", letter: "P" },
  { id: "icloud", label: "iCloud+", color: "#3693F6", letter: "i" },
] as const;
const subOf = (id: string | null) => SUBS.find((s) => s.id === id);

/* Kategori renk paleti — donut ve rozetlerde sabit dagilim */
const PALETTE = ["#6C4CFF", "#1DB954", "#F59E0B", "#EF4444", "#3693F6", "#14B8A6", "#EC4899", "#8B5CF6", "#F97316", "#64748B"];
const colorOf = (index: number) => PALETTE[index % PALETTE.length];

function SubLogo({ sub, size = 22 }: { sub: string | null; size?: number }) {
  const hit = subOf(sub);
  if (!hit) return null;
  return (
    <span
      title={hit.label}
      className="flex shrink-0 select-none items-center justify-center rounded-full font-medium text-canvas"
      style={{ background: hit.color, width: size, height: size, fontSize: size * 0.5 }}
    >
      {hit.letter}
    </span>
  );
}

/* Dairesel pasta (donut) — SVG, ek bagimlilik yok */
function Donut({ segments }: { segments: { label: string; value: number; color: string }[] }) {
  const total = segments.reduce((acc, s) => acc + s.value, 0);
  const R = 42;
  const C = 2 * Math.PI * R;
  let acc = 0;
  return (
    <div className="flex flex-wrap items-center gap-5">
      <svg viewBox="0 0 100 100" className="h-36 w-36 shrink-0 -rotate-90">
        <circle cx="50" cy="50" r={R} fill="none" stroke="var(--surface-sunken)" strokeWidth="14" />
        {segments.map((s) => {
          const frac = s.value / (total || 1);
          const dash = frac * C;
          const el = (
            <circle
              key={s.label}
              cx="50" cy="50" r={R}
              fill="none"
              stroke={s.color}
              strokeWidth="14"
              strokeDasharray={`${dash} ${C - dash}`}
              strokeDashoffset={-acc * C}
            />
          );
          acc += frac;
          return el;
        })}
      </svg>
      <div className="min-w-0 flex-1 space-y-1">
        {segments.map((s) => (
          <div key={s.label} className="flex items-center gap-2 text-meta">
            <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: s.color }} />
            <span className="truncate text-secondary">{s.label}</span>
            <span className="numeral ml-auto font-medium text-primary">{Math.round(s.value).toLocaleString("tr-TR")}</span>
          </div>
        ))}
        <div className="flex items-center gap-2 border-t border-subtle pt-1.5 text-meta">
          <span className="text-muted">Toplam</span>
          <span className="numeral ml-auto font-medium text-primary">{Math.round(total).toLocaleString("tr-TR")}</span>
        </div>
      </div>
    </div>
  );
}

export function FinancePage() {
  const [tab, setTab] = useState<"budget" | "expenses" | "recurring">("budget");
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("other");
  const [sub, setSub] = useState("");
  const invalidate = useInvalidate();
  const now = new Date();
  const online = useOnline();
  const { data: expenses = [] } = useQuery({ queryKey: ["expenses"], queryFn: () => api.get<Expense[]>("/expenses") });
  const { data: recurring = [] } = useQuery({ queryKey: ["recurring"], queryFn: () => api.get<RecurringPayment[]>("/recurring-payments") });
  const { data: summary = [] } = useQuery({ queryKey: ["expense-summary"], queryFn: () => api.get<Summary[]>("/expenses/summary") });

  const refresh = () => invalidate("expenses", "recurring", "expense-summary", "deadlines", "activity");
  const create = useMutation({
    mutationFn: () =>
      tab === "expenses"
        ? api.post("/expenses", { title, amount, category, sub: sub || null })
        : api.post("/recurring-payments", { title, amount, category: sub ? "subscriptions" : category, sub: sub || null, next_due_at: localDateKey(now) }),
    onSuccess: () => { setTitle(""); setAmount(""); setSub(""); refresh(); },
  });
  const remove = useMutation({
    mutationFn: ({ id, kind }: { id: string; kind: "expenses" | "recurring-payments" }) => api.del("/" + kind + "/" + id),
    onSuccess: refresh,
  });
  const pay = useMutation({
    mutationFn: (id: string) => api.post("/recurring-payments/" + id + "/pay"),
    onSuccess: refresh,
  });

  /* Donut segmentleri: kur bazinda, kategori bazinda toplam */
  const byCurrency = summary.reduce<Record<string, Summary[]>>((acc, row) => {
    (acc[row.currency] ??= []).push(row);
    return acc;
  }, {});

  function BrandPicker() {
    return (
      <div className="flex flex-wrap gap-1.5">
        <button type="button" onClick={() => setSub("")}
          className={cxSub(!sub)}>
          <span className="h-[22px] w-[22px] rounded-full border border-subtle bg-surface-sunken" />
          Yok
        </button>
        {SUBS.map((s) => (
          <button key={s.id} type="button" onClick={() => setSub(sub === s.id ? "" : s.id)}
            className={cxSub(sub === s.id)}>
            <SubLogo sub={s.id} />
            {s.label}
          </button>
        ))}
      </div>
    );
    function cxSub(active: boolean) {
      return "flex h-8 items-center gap-1.5 rounded-control border px-2.5 text-meta transition " +
        (active ? "border-accent bg-accent-surface font-medium text-accent" : "border-subtle text-secondary hover:bg-surface-hover");
    }
  }

  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Takip" title="Finans" />
      <p className="text-meta text-muted">Kur dönüşümü yok; her para birimi kendi toplamında kalır.</p>
      <Toolbar>
        <Button variant={tab === "budget" ? "primary" : "ghost"} onClick={() => setTab("budget")}>Bütçe</Button>
        <Button variant={tab === "expenses" ? "primary" : "ghost"} onClick={() => setTab("expenses")}>Harcamalar</Button>
        <Button variant={tab === "recurring" ? "primary" : "ghost"} onClick={() => setTab("recurring")}>Abonelikler</Button>
      </Toolbar>

      {tab === "budget" && (
        <Section title="Bu ay · bütçe dağılımı">
          {Object.keys(byCurrency).length === 0 ? (<Empty>Bu ay harcama yok.</Empty>) : (
            <div className="grid gap-6 lg:grid-cols-2">
              {Object.entries(byCurrency).map(([currency, rows]) => {
                const segments = rows
                  .slice()
                  .sort((a, b) => Number(b.amount) - Number(a.amount))
                  .map((row, i) => ({ label: row.category, value: Number(row.amount), color: colorOf(i) }));
                return (
                  <div key={currency} className="rounded-card border border-subtle bg-surface p-4">
                    <h3 className="mb-3 text-heading text-primary">Dağılım · {currency}</h3>
                    <Donut segments={segments} />
                  </div>
                );
              })}
            </div>
          )}
        </Section>
      )}

      {(tab === "expenses" || tab === "recurring") && (
        <Toolbar>
          <form
            className="grid w-full gap-2 md:grid-cols-[1fr_9rem_10rem_auto]"
            onSubmit={(e) => { e.preventDefault(); if (title.trim() && Number(amount) > 0) create.mutate(); }}
          >
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={tab === "expenses" ? "Harcama" : "Abonelik ödemesi"} className="rounded border border-subtle bg-canvas px-3 py-2 text-body" />
            <input type="number" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Tutar TRY" className="rounded border border-subtle bg-canvas px-3 py-2 text-body" />
            {tab === "expenses" && (
              <select value={category} onChange={(e) => setCategory(e.target.value)} className="rounded border border-subtle bg-canvas px-3 py-2 text-body">
                {categories.map((x) => <option key={x}>{x}</option>)}
              </select>
            )}
            <Button type="submit" variant="primary" disabled={!online || create.isPending}>Ekle</Button>
          </form>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-meta text-muted">{tab === "expenses" ? "Tür:" : "Abonelik:"}</span>
            <BrandPicker />
          </div>
        </Toolbar>
      )}

      {tab === "expenses" && (
        <Section title="Bu ay">
          <RowList>
            {expenses.map((x) => (
              <div key={x.id} className="group flex items-center justify-between gap-3 py-3 text-body">
                <div className="flex min-w-0 items-center gap-2.5">
                  {x.sub && <SubLogo sub={x.sub} size={20} />}
                  <span className="min-w-0">
                    <span className="block truncate">{x.title}</span>
                    <p className="text-meta text-muted">{x.spent_on} · {x.category}{x.sub ? " · abonelik" : ""}</p>
                  </span>
                </div>
                <strong className="shrink-0">{Number(x.amount).toLocaleString("tr-TR")} {x.currency}</strong>
                <IconButton title="Sil" tone="danger" disabled={!online} className="shrink-0 opacity-0 transition group-hover:opacity-100" onClick={() => remove.mutate({ id: x.id, kind: "expenses" })}>
                  <Trash2 size={14} />
                </IconButton>
              </div>
            ))}
          </RowList>
        </Section>
      )}

      {tab === "recurring" && (
        <Section title="Abonelikler (düzenli ödemeler)">
          <RowList>
            {recurring.map((x) => (
              <div key={x.id} className="group flex flex-wrap items-center gap-3 py-3">
                <SubLogo sub={x.sub} size={26} />
                <div className="min-w-0 flex-1">
                  <p className="text-body text-primary">{x.title}{x.sub ? " · " + (subOf(x.sub)?.label ?? x.sub) : ""}</p>
                  <p className="text-meta text-muted">Sonraki: {x.next_due_at ?? "belirsiz"}</p>
                </div>
                <Badge tone={x.active ? "ok" : "neutral"}>{x.frequency}</Badge>
                <strong>{Number(x.amount).toLocaleString("tr-TR")} {x.currency}</strong>
                <Button variant="primary" disabled={!online || pay.isPending} onClick={() => pay.mutate(x.id)}>Ödendi</Button>
                <IconButton title="Sil" tone="danger" disabled={!online} className="opacity-0 transition group-hover:opacity-100" onClick={() => remove.mutate({ id: x.id, kind: "recurring-payments" })}>
                  <Trash2 size={14} />
                </IconButton>
              </div>
            ))}
          </RowList>
        </Section>
      )}

      {((tab === "expenses" && !expenses.length) || (tab === "recurring" && !recurring.length)) && <Empty>Kayıt yok.</Empty>}
    </PageFrame>
  );
}