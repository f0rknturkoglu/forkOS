import { useMutation } from "@tanstack/react-query";
import { Check, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import type { RecurringPayment } from "@/core/types";
import { Button, Chip, Empty, IconButton, Metric, MetricStrip, RowList, Section, useToast } from "@/core/ui";
import { daysBetween, todayKey } from "@/lib/date";
import { billingLabel, dueLabel, frequencyLabel, money, moneyShort, monthlyShare } from "./financeLabels";
import { SubBadge } from "./SubBadge";

/** Geri sayim cipi: yaklastikca uyariya doner, gecikmis odeme kirmizi. */
function dueChip(item: RecurringPayment) {
  if (!item.next_due_at) return null;
  const days = daysBetween(todayKey(), item.next_due_at);
  const tone = days < 0 ? "danger" : days <= 3 ? "warn" : "neutral";
  return <Chip tone={tone}>{dueLabel(days)}</Chip>;
}

/**
 * Abonelikler: gelecege donuk duzenli taahhutler (gecmis harcama degil).
 *
 * Bu yuzden sayfa "ne harcadim" degil "her ay ne kadar sabit yuk tasiyorum"
 * sorusunu once cevaplar: aylik yuk ve yillik izdusum kartlari ustte durur.
 */
export function FinanceSubscriptionsTab({ recurring, online }: { recurring: RecurringPayment[]; online: boolean }) {
  const toast = useToast();
  const active = recurring.filter((item) => item.active);
  const paused = recurring.filter((item) => !item.active);

  const monthly = active.reduce((sum, item) => sum + monthlyShare(item.amount, item.frequency), 0);
  const currency = active[0]?.currency ?? "TRY";

  const pay = useMutation({
    mutationFn: (id: string) => api.post(`/recurring-payments/${id}/pay`),
    onSuccess: (_result, id) => {
      const item = active.find((entry) => entry.id === id);
      invalidateAfter("finance.write");
      toast.push(
        item
          ? `${item.title} ödemesi yapıldı ve bu ayın harcamalarına eklendi.`
          : "Ödeme yapıldı ve bu ayın harcamalarına eklendi.",
        { tone: "ok" },
      );
    },
    onError: (error) => toast.push(`Ödeme işlenemedi: ${error.message}`, { tone: "danger" }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/recurring-payments/${id}`),
    onSuccess: () => {
      invalidateAfter("finance.write");
      toast.push("Abonelik silindi.", { tone: "neutral" });
    },
    onError: (error) => toast.push(`Silinemedi: ${error.message}`, { tone: "danger" }),
  });

  async function confirmRemove(item: RecurringPayment) {
    const ok = await confirmDialog({
      title: "Abonelik silinsin mi?",
      body: `${item.title} · ${money(item.amount, item.currency)} / ${frequencyLabel(item.frequency)}`,
      confirmLabel: "Sil",
      tone: "danger",
    });
    if (ok) remove.mutate(item.id);
  }

  return (
    <div className="space-y-5">
      <MetricStrip className="grid-cols-2">
        <Metric
          label="Aylık sabit yük"
          value={<span className="numeral tabular-nums">{moneyShort(monthly, currency)}</span>}
          hint={`${active.length} aktif abonelik`}
        />
        <Metric
          label="Yıllık izdüşüm"
          value={<span className="numeral tabular-nums">{moneyShort(monthly * 12, currency)}</span>}
          hint="aynı düzen 12 ay sürerse"
        />
      </MetricStrip>

      {active.length === 0 ? (
        <Empty variant="page" title="Abonelik yok">
          Netflix, Spotify, iCloud… Yeni ekle düğmesiyle abonelik ekle; her ay ne kadar sabit gider taşıdığını burada
          gör.
        </Empty>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {active.map((item) => (
            <div key={item.id} className="flex flex-col gap-3 rounded-card border border-subtle bg-surface p-4">
              <div className="flex items-start gap-2.5">
                <SubBadge sub={item.sub} title={item.title} size={30} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-heading text-primary">{item.title}</p>
                  <p className="text-meta text-muted">{billingLabel(item.frequency, item.billing_day)}</p>
                </div>
                <IconButton title="Sil" tone="danger" disabled={!online} onClick={() => void confirmRemove(item)}>
                  <Trash2 size={14} />
                </IconButton>
              </div>
              <div className="flex items-baseline justify-between gap-2">
                <strong className="numeral text-title text-primary">
                  {money(item.amount, item.currency)}
                  <span className="ml-1 text-meta font-normal text-muted">/{frequencyLabel(item.frequency)}</span>
                </strong>
                {dueChip(item)}
              </div>
              <Button
                variant="primary"
                disabled={!online || pay.isPending}
                onClick={() => pay.mutate(item.id)}
                className="w-full"
              >
                <Check size={14} /> Ödendi
              </Button>
            </div>
          ))}
        </div>
      )}

      {paused.length > 0 && (
        <Section title="Duraklatılmış">
          <RowList>
            {paused.map((item) => (
              <div key={item.id} className="flex items-center gap-3 py-2.5 text-body text-secondary">
                <SubBadge sub={item.sub} title={item.title} size={20} />
                <span className="min-w-0 flex-1 truncate">{item.title}</span>
                <span className="text-meta text-muted">{billingLabel(item.frequency, item.billing_day)}</span>
                <span className="numeral shrink-0 tabular-nums">{money(item.amount, item.currency)}</span>
                <IconButton title="Sil" tone="danger" disabled={!online} onClick={() => void confirmRemove(item)}>
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
