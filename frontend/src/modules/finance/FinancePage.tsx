import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BarChart3, ChevronLeft, ChevronRight, CreditCard, Plus, ReceiptText } from "lucide-react";
import { api, qs } from "@/core/api";
import { navigate, useHashRoute } from "@/app/router";
import { invalidateAfter } from "@/core/invalidation";
import { RelatedPanel } from "@/core/RelatedPanel";
import type { Expense, FinanceOverview, Income, RecurringPayment } from "@/core/types";
import { Button, FilterChip, IconButton, PageFrame, Section, useToast } from "@/core/ui";
import {
  Workspace,
  WorkspacePaneHeader,
  WorkspaceRailButton,
  WorkspaceRailContent,
  WorkspaceRailGroup,
  WorkspaceScrollArea,
} from "@/core/workspace/Workspace";
import { todayKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { AddTransactionDialog, type TransactionKind } from "./AddTransactionDialog";
import { FinanceOverviewTab, type MonthlySummary } from "./FinanceOverviewTab";
import { FinanceSubscriptionsTab } from "./FinanceSubscriptionsTab";
import { FinanceTransactionsTab, buildFlows } from "./FinanceTransactionsTab";
import { monthKeyOf, monthLabel, parseMonth, shiftMonth } from "./financeLabels";

type Tab = "summary" | "flow" | "subs";
const TABS: { id: Tab; label: string; icon: typeof BarChart3 }[] = [
  { id: "summary", label: "Özet", icon: BarChart3 },
  { id: "flow", label: "Hareketler", icon: ReceiptText },
  { id: "subs", label: "Abonelikler", icon: CreditCard },
];

/** Kisa yol metin alanlarinda calismaz (yazarken harf yutmasin). */
function isTypingTarget(target: EventTarget | null): boolean {
  const element = target as HTMLElement | null;
  return (
    !!element && (element.tagName === "INPUT" || element.tagName === "TEXTAREA" || element.isContentEditable === true)
  );
}

/**
 * Finans: ozet, hareketler ve abonelikler tek sayfada; secili ay ve para
 * birimi URL'de yasar. Ekleme/duzeltme artik acik formlar degil, modallar
 * uzerinden yapilir -- sayfa listeleme ve analiz yuzeyi olarak kalir.
 */
export function FinancePage() {
  const route = useHashRoute();
  const focusId = route.params.get("focus") ?? "";
  const tab = (TABS.find((item) => item.id === route.params.get("tab"))?.id ?? "summary") as Tab;
  const month = route.params.get("month") ?? monthKeyOf(todayKey());
  const thisMonth = monthKeyOf(todayKey());
  const online = useOnline();
  const toast = useToast();

  const [addOpen, setAddOpen] = useState(false);
  const [addKind, setAddKind] = useState<TransactionKind>("expense");
  const [currencyParam, setCurrencyParam] = useState<string | null>(route.params.get("cur"));

  const go = (next: { tab?: Tab; month?: string; cur?: string }) =>
    navigate(
      "/finance" +
        qs({
          tab: next.tab ?? tab,
          month: next.month ?? month,
          cur: next.cur ?? currencyParam ?? undefined,
          focus: focusId,
        }),
    );

  const { year, month: monthNumber } = parseMonth(month);
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<Record<string, unknown>>("/settings"),
  });
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

  const saveBudget = useMutation({
    mutationFn: (next: Record<string, number>) => api.put("/settings/finance.monthly_budget", { value: next }),
    onSuccess: () => {
      invalidateAfter("settings.write");
      toast.push("Bütçe kaydedildi.", { tone: "ok" });
    },
    onError: (error) => toast.push(`Bütçe kaydedilemedi: ${error.message}`, { tone: "danger" }),
  });

  /* Para birimi: URL'de secili olan; yoksa hareketi en yogun olan. */
  const currencies = useMemo(() => {
    const seen = new Set<string>();
    for (const row of overview?.currencies ?? []) seen.add(row.currency.trim());
    for (const row of expenses) seen.add(row.currency.trim());
    for (const row of incomes) seen.add(row.currency.trim());
    return [...seen].filter(Boolean);
  }, [overview, expenses, incomes]);
  const currency = currencyParam && currencies.includes(currencyParam) ? currencyParam : (currencies[0] ?? "TRY");

  const row = useMemo(() => {
    const hit = (overview?.currencies ?? []).find((item) => item.currency.trim() === currency);
    return (
      hit ?? {
        currency,
        income: "0",
        expense: "0",
        net: "0",
        recurring_monthly: "0",
        expense_by_category: [],
        income_by_category: [],
      }
    );
  }, [overview, currency]);

  const flows = useMemo(
    () =>
      buildFlows(
        expenses.filter((item) => item.currency.trim() === currency),
        incomes.filter((item) => item.currency.trim() === currency),
        month,
      ),
    [expenses, incomes, currency, month],
  );
  const recurringInCurrency = useMemo(
    () => recurring.filter((item) => item.currency.trim() === currency),
    [recurring, currency],
  );

  const budgetMap = (settings?.["finance.monthly_budget"] ?? {}) as Record<string, number>;
  const budget = typeof budgetMap[currency] === "number" ? budgetMap[currency] : null;

  /* Klavyeden hizli ekleme: "n" (metin alanlari haric). */
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (isTypingTarget(event.target) || event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.key.toLowerCase() !== "n" || addOpen) return;
      event.preventDefault();
      setAddOpen(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [addOpen]);

  function openAdd(kind: TransactionKind) {
    setAddKind(kind);
    setAddOpen(true);
  }

  return (
    <PageFrame className="py-3">
      <Workspace
        railAt="lg"
        rail={
          <WorkspaceRailContent className="max-h-44 lg:max-h-workspace-body">
            <WorkspaceRailGroup label="Finans görünümleri">
              {TABS.map((item) => {
                const Icon = item.icon;
                return (
                  <WorkspaceRailButton
                    key={item.id}
                    label={item.label}
                    icon={<Icon size={13} />}
                    active={tab === item.id}
                    onClick={() => go({ tab: item.id })}
                  />
                );
              })}
            </WorkspaceRailGroup>
          </WorkspaceRailContent>
        }
      >
        <WorkspacePaneHeader
          eyebrow="Finans"
          title={monthLabel(month)}
          hint={`${currency} · ${flows.length} hareket`}
          action={
            <div className="flex items-center gap-1">
              <IconButton title="Önceki ay" onClick={() => go({ month: shiftMonth(month, -1) })}>
                <ChevronLeft size={15} />
              </IconButton>
              {month !== thisMonth ? (
                <Button size="sm" onClick={() => go({ month: thisMonth })}>
                  Bu ay
                </Button>
              ) : null}
              <IconButton title="Sonraki ay" onClick={() => go({ month: shiftMonth(month, 1) })}>
                <ChevronRight size={15} />
              </IconButton>
              <Button
                variant="primary"
                title="Yeni ekle (kısayol: n)"
                onClick={() => openAdd(tab === "subs" ? "subscription" : "expense")}
              >
                <Plus size={14} /> Yeni ekle
              </Button>
            </div>
          }
        >
          <div className="flex flex-wrap items-center gap-1.5">
            {currencies.map((item) => (
              <FilterChip
                key={item}
                label={item.trim()}
                active={currency === item}
                onClick={() => {
                  setCurrencyParam(item);
                  go({ cur: item });
                }}
              />
            ))}
          </div>
        </WorkspacePaneHeader>

        <WorkspaceScrollArea className="space-y-5 p-3">
          {tab === "summary" && (
            <FinanceOverviewTab
              row={row}
              summary={summary}
              recurring={recurringInCurrency}
              budget={budget}
              onBudget={(value) => {
                const next = { ...budgetMap };
                if (value === null) delete next[currency];
                else next[currency] = value;
                saveBudget.mutate(next);
              }}
              online={online}
            />
          )}
          {tab === "flow" && <FinanceTransactionsTab flows={flows} month={month} online={online} />}
          {tab === "subs" && <FinanceSubscriptionsTab recurring={recurringInCurrency} online={online} />}

          {focusId && (
            <Section title="Bağlı kayıtlar">
              <RelatedPanel entityId={focusId} />
            </Section>
          )}
        </WorkspaceScrollArea>
      </Workspace>

      {/* Kosullu mount: her acilista temiz bir form (tur secimi ve alanlar sifirlanir). */}
      {addOpen && (
        <AddTransactionDialog
          open
          onClose={() => setAddOpen(false)}
          currency={currency}
          defaultKind={addKind}
          online={online}
        />
      )}
    </PageFrame>
  );
}
