import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useHashRoute } from "@/app/router";
import { api } from "@/core/api";
import { RelatedPanel } from "@/core/RelatedPanel";
import type { RecurringPayment } from "@/core/types";
import { Button, FilterChip, PageFrame, RowList, Section } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { daysBetween, todayKey } from "@/lib/date";
import { formatTrDateTime } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { AddTransactionDialog } from "./AddTransactionDialog";
import { FinanceSubscriptionsTab } from "./FinanceSubscriptionsTab";
import { dueLabel, money } from "./financeLabels";
import { RECURRING_PAYMENTS_QUERY_KEY } from "./queries";

/** Eski finans rotası korunur; kullanıcı yüzeyi abonelik ve ödeme takibidir. */
export function FinancePage() {
  const { params } = useHashRoute();
  const [addOpen, setAddOpen] = useState(false);
  const [currency, setCurrency] = useState<string | null>(null);
  const online = useOnline();
  const { data: recurring = [] } = useQuery({
    queryKey: RECURRING_PAYMENTS_QUERY_KEY,
    queryFn: () => api.get<RecurringPayment[]>("/recurring-payments"),
  });
  const { data: paid = [] } = useQuery({
    queryKey: ["recurring-history"],
    queryFn: () => api.get<{ id: number; title: string; paid_at: string }[]>("/recurring-payments/history"),
  });
  const currencies = [...new Set(recurring.map((item) => item.currency.trim()))];
  const selected = currency && currencies.includes(currency) ? currency : (currencies[0] ?? "TRY");
  const items = recurring.filter((item) => item.currency.trim() === selected);
  const upcoming = items
    .filter((item) => item.active && item.next_due_at)
    .sort((a, b) => (a.next_due_at ?? "").localeCompare(b.next_due_at ?? ""));
  const dueSoon = upcoming.filter((item) => daysBetween(todayKey(), item.next_due_at ?? todayKey()) <= 30);
  const focusId = params.get("focus");

  return (
    <PageFrame className="py-3">
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Kişisel takip"
          title="Abonelikler"
          hint={`${items.filter((item) => item.active).length} aktif abonelik`}
          action={
            <Button variant="primary" onClick={() => setAddOpen(true)}>
              <Plus size={14} /> Abonelik ekle
            </Button>
          }
        >
          <div className="flex flex-wrap gap-1.5">
            {currencies.map((item) => (
              <FilterChip key={item} label={item} active={selected === item} onClick={() => setCurrency(item)} />
            ))}
          </div>
        </WorkspacePaneHeader>
        <WorkspaceScrollArea className="space-y-5 p-3">
          <Section title="Yaklaşan ödemeler" hint="önümüzdeki 30 gün">
            {dueSoon.length === 0 ? (
              <p className="text-meta text-muted">Yaklaşan ödeme yok.</p>
            ) : (
              <RowList>
                {dueSoon.map((item) => {
                  const days = daysBetween(todayKey(), item.next_due_at ?? todayKey());
                  return (
                    <div key={item.id} className="flex items-center gap-3 py-2 text-body">
                      <span className="min-w-0 flex-1 truncate text-primary">{item.title}</span>
                      <span className="text-meta text-muted">
                        {days <= 7 ? "7 gün" : "30 gün"} · {dueLabel(days)}
                      </span>
                      <span className="tabular-nums text-secondary">{money(item.amount, item.currency)}</span>
                    </div>
                  );
                })}
              </RowList>
            )}
          </Section>
          <FinanceSubscriptionsTab recurring={items} online={online} />
          <Section title="Ödendi / Geçmiş" hint={`${paid.length} ödeme`}>
            {paid.length === 0 ? (
              <p className="text-meta text-muted">Henüz kayıtlı ödeme yok.</p>
            ) : (
              <RowList>
                {paid.map((item) => (
                  <div key={item.id} className="flex items-center gap-3 py-2 text-body">
                    <span className="min-w-0 flex-1 truncate text-primary">{item.title}</span>
                    <span className="text-meta text-muted">
                      {formatTrDateTime(item.paid_at, { day: "numeric", month: "short", year: "numeric" })}
                    </span>
                  </div>
                ))}
              </RowList>
            )}
          </Section>
          {focusId && (
            <Section title="Bağlı kayıtlar">
              <RelatedPanel entityId={focusId} />
            </Section>
          )}
        </WorkspaceScrollArea>
      </Workspace>
      {addOpen && (
        <AddTransactionDialog
          open
          onClose={() => setAddOpen(false)}
          currency={selected}
          defaultKind="subscription"
          online={online}
        />
      )}
    </PageFrame>
  );
}
