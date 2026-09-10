import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowDownLeft, ArrowUpRight, Repeat, Wallet } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Field, FilterChip, Input, Modal, NumberInput, Select, cx, useToast } from "@/core/ui";
import { todayKey } from "@/lib/date";
import {
  categoryIcon,
  categoryLabel,
  EXPENSE_CATEGORIES,
  FREQUENCIES,
  frequencyLabel,
  INCOME_CATEGORIES,
  subSlug,
} from "./financeLabels";

/** Tek modalda uc is: gider, gelir ve abonelik (gelecege donuk taahhut). */
export type TransactionKind = "expense" | "income" | "subscription";

const KINDS: { id: TransactionKind; label: string; icon: typeof Wallet }[] = [
  { id: "expense", label: "Gider", icon: ArrowDownLeft },
  { id: "income", label: "Gelir", icon: ArrowUpRight },
  { id: "subscription", label: "Abonelik", icon: Repeat },
];

const DEFAULT_CATEGORY: Record<TransactionKind, string> = {
  expense: "food",
  income: "salary",
  subscription: "subscriptions",
};

/** Sonraki vade: bu ayin odeme gunu gectiyse gelecek ay (takvim gunu tasmaz). */
function nextDue(day: number): string {
  const today = todayKey();
  const [year, month] = today.split("-").map(Number);
  const inMonth = Math.min(day, new Date(Date.UTC(year, month, 0)).getUTCDate());
  const candidate = `${year}-${String(month).padStart(2, "0")}-${String(inMonth).padStart(2, "0")}`;
  if (candidate >= today) return candidate;
  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear = month === 12 ? year + 1 : year;
  const clamped = Math.min(day, new Date(Date.UTC(nextYear, nextMonth, 0)).getUTCDate());
  return `${nextYear}-${String(nextMonth).padStart(2, "0")}-${String(clamped).padStart(2, "0")}`;
}

/**
 * Hizli ekleme modali. Sayfadaki acik formlar yerine tek yuzey: tur secimi
 * (gider/gelir/abonelik), buyuk tutar girisi, ikonlu kategori cipleri ve
 * tarih. Abonelikte siklik + odeme gunu alanlari acilir.
 */
export function AddTransactionDialog({
  open,
  onClose,
  currency,
  defaultKind = "expense",
  online,
}: {
  open: boolean;
  onClose: () => void;
  currency: string;
  defaultKind?: TransactionKind;
  online: boolean;
}) {
  const toast = useToast();
  const [kind, setKind] = useState<TransactionKind>(defaultKind);
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState(DEFAULT_CATEGORY[defaultKind]);
  const [note, setNote] = useState("");
  const [day, setDay] = useState(todayKey());
  const [frequency, setFrequency] = useState("monthly");
  const [billingDay, setBillingDay] = useState(1);

  const amountValue = Number(amount);
  const valid = title.trim().length > 0 && Number.isFinite(amountValue) && amountValue > 0;

  const create = useMutation({
    mutationFn: () => {
      if (kind === "subscription") {
        return api.post("/recurring-payments", {
          title: title.trim(),
          amount,
          currency,
          category,
          frequency,
          billing_day: billingDay,
          next_due_at: nextDue(billingDay),
          // Marka slug'i addan turetilir -- kullaniciya marka sectirilmez.
          sub: subSlug(title.trim()),
          note: note.trim() || null,
        });
      }
      const body = {
        title: title.trim(),
        amount,
        currency,
        category,
        note: note.trim() || null,
      };
      return kind === "expense"
        ? api.post("/expenses", { ...body, spent_on: day })
        : api.post("/incomes", { ...body, received_on: day });
    },
    onSuccess: () => {
      invalidateAfter("finance.write");
      toast.push(kind === "subscription" ? `${title.trim()} aboneliği eklendi.` : `${title.trim()} kaydedildi.`, {
        tone: "ok",
      });
      reset();
      onClose();
    },
    onError: (error) => toast.push(`Kaydedilemedi: ${error.message}`, { tone: "danger" }),
  });

  function reset() {
    setTitle("");
    setAmount("");
    setNote("");
    setDay(todayKey());
  }

  /** Tur degisince kategori o turun gecerli listesine duser. */
  function switchKind(next: TransactionKind) {
    setKind(next);
    setCategory(DEFAULT_CATEGORY[next]);
  }

  const categories = kind === "income" ? INCOME_CATEGORIES : EXPENSE_CATEGORIES;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Yeni ekle"
      hint={`${currency} · tutar ve kategori yeterli`}
      footer={
        <div className="flex items-center justify-end gap-2">
          <Button onClick={onClose}>Vazgeç</Button>
          <Button
            variant="primary"
            disabled={!online || !valid || create.isPending}
            onClick={() => create.mutate()}
            ariaLabel="Kaydet"
          >
            Kaydet
          </Button>
        </div>
      }
    >
      <div className="mb-4 flex gap-1.5" role="tablist" aria-label="Kayıt türü">
        {KINDS.map((item) => {
          const Icon = item.icon;
          return (
            <FilterChip
              key={item.id}
              label={item.label}
              icon={<Icon size={13} />}
              active={kind === item.id}
              onClick={() => switchKind(item.id)}
            />
          );
        })}
      </div>

      <div className="mb-4">
        <Field label="Tutar">
          <div className="flex items-end gap-2">
            <NumberInput
              value={Number.isFinite(amountValue) && amount !== "" ? amountValue : NaN}
              onChange={(next) => setAmount(Number.isFinite(next) ? String(next) : "")}
              placeholder="0,00"
              min={0}
              step={0.01}
              ariaLabel="Tutar"
              className="text-title"
            />
            <span className="pb-1 text-body text-muted">{currency}</span>
          </div>
        </Field>
      </div>

      <Field label={kind === "subscription" ? "Abonelik adı" : "Açıklama"}>
        <Input
          value={title}
          onChange={setTitle}
          placeholder={kind === "income" ? "Ağustos maaşı" : kind === "subscription" ? "Netflix" : "Market"}
          ariaLabel={kind === "subscription" ? "Abonelik adı" : "Açıklama"}
        />
      </Field>

      <div className="mt-3">
        <p className="mb-0.5 text-meta text-secondary">Kategori</p>
        <div className="flex flex-wrap gap-1.5">
          {categories.map((item) => {
            const Icon = categoryIcon(item);
            return (
              <FilterChip
                key={item}
                label={categoryLabel(item)}
                icon={<Icon size={13} />}
                active={category === item}
                onClick={() => setCategory(item)}
              />
            );
          })}
        </div>
      </div>

      {kind === "subscription" ? (
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Field label="Sıklık">
            <Select value={frequency} onChange={setFrequency} ariaLabel="Sıklık">
              {FREQUENCIES.map((item) => (
                <option key={item} value={item}>
                  {frequencyLabel(item)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Ödeme günü">
            <NumberInput value={billingDay} onChange={setBillingDay} min={1} max={31} step={1} ariaLabel="Ödeme günü" />
          </Field>
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Field label="Tarih">
            <Input type="date" value={day} onChange={setDay} ariaLabel="Tarih" />
          </Field>
          <Field label="Not (isteğe bağlı)">
            <Input value={note} onChange={setNote} placeholder="Opsiyonel" ariaLabel="Not" />
          </Field>
        </div>
      )}

      {kind === "subscription" && (
        <p className={cx("mt-3 text-meta text-muted")}>
          Abonelik gelecek aylara işler; ödediğinde ilgili günün harcaması olarak kaydedilir.
        </p>
      )}
    </Modal>
  );
}
