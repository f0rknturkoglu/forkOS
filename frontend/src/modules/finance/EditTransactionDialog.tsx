import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Chip, Field, FilterChip, Input, Modal, NumberInput, useToast } from "@/core/ui";
import { categoryIcon, categoryLabel, EXPENSE_CATEGORIES, INCOME_CATEGORIES } from "./financeLabels";

/** Duzeltilebilen tek hareket -- gelir ve gider ayni sekle indirgenir. */
export interface EditableTransaction {
  id: string;
  title: string;
  /** JSON'da sayi gelebilir (bkz. core/types.ts Expense.amount). */
  amount: string | number;
  currency: string;
  category: string;
  /** ISO gun: giderde spent_on, gelirde received_on. */
  day: string;
  kind: "income" | "expense";
}

/**
 * Hareket duzenleme modali: tutar, baslik, kategori ve tarih; ayrica silme.
 *
 * Satir ici duzenleme formu listeyi bozuyordu (her satir kendi input'unu
 * tasiyinca gun bloklari kayiyordu); duzenleme tek yuzeye tasindi.
 */
export function EditTransactionDialog({
  transaction,
  onClose,
  online,
}: {
  transaction: EditableTransaction | null;
  onClose: () => void;
  online: boolean;
}) {
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("other");
  const [day, setDay] = useState("");

  const open = transaction !== null;
  useEffect(() => {
    if (!transaction) return;
    setTitle(transaction.title);
    setAmount(String(transaction.amount));
    setCategory(transaction.category);
    setDay(transaction.day);
  }, [transaction]);

  const dateKey = transaction?.kind === "income" ? "received_on" : "spent_on";
  const categories = transaction?.kind === "income" ? INCOME_CATEGORIES : EXPENSE_CATEGORIES;
  const amountValue = Number(amount);
  const valid = title.trim().length > 0 && Number.isFinite(amountValue) && amountValue > 0;

  const update = useMutation({
    // Yol degiskenle kurulmaz: uctan uca kapsam betigi literal cagriyi arar.
    mutationFn: () => {
      const id = transaction?.id;
      const body = { title: title.trim(), amount, category, [dateKey]: day };
      return transaction?.kind === "income" ? api.patch(`/incomes/${id}`, body) : api.patch(`/expenses/${id}`, body);
    },
    onSuccess: () => {
      invalidateAfter("finance.write");
      toast.push("Hareket güncellendi.", { tone: "ok" });
      onClose();
    },
    onError: (error) => toast.push(`Güncellenemedi: ${error.message}`, { tone: "danger" }),
  });

  const remove = useMutation({
    mutationFn: () =>
      transaction?.kind === "income" ? api.del(`/incomes/${transaction?.id}`) : api.del(`/expenses/${transaction?.id}`),
    onSuccess: () => {
      invalidateAfter("finance.write");
      toast.push("Hareket silindi.", { tone: "neutral" });
      onClose();
    },
    onError: (error) => toast.push(`Silinemedi: ${error.message}`, { tone: "danger" }),
  });

  async function confirmRemove() {
    if (!transaction) return;
    const ok = await confirmDialog({
      title: "Hareket silinsin mi?",
      body: `${transaction.title} · ${transaction.amount} ${transaction.currency}`,
      confirmLabel: "Sil",
      tone: "danger",
    });
    if (ok) remove.mutate();
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Hareketi düzenle"
      hint={transaction ? `${transaction.currency} · ${transaction.day}` : undefined}
      ariaLabel="Hareketi düzenle"
      footer={
        <div className="flex items-center justify-between gap-2">
          <Button variant="danger" disabled={!online || remove.isPending} onClick={confirmRemove}>
            <Trash2 size={14} /> Sil
          </Button>
          <div className="flex items-center gap-2">
            <Button onClick={onClose}>Vazgeç</Button>
            <Button
              variant="primary"
              disabled={!online || !valid || update.isPending}
              onClick={() => update.mutate()}
              ariaLabel="Kaydet"
            >
              Kaydet
            </Button>
          </div>
        </div>
      }
    >
      <Field label="Tutar">
        <div className="flex items-end gap-2">
          <NumberInput
            value={Number.isFinite(amountValue) && amount !== "" ? amountValue : NaN}
            onChange={(next) => setAmount(Number.isFinite(next) ? String(next) : "")}
            min={0}
            step={0.01}
            ariaLabel="Tutar"
            className="text-title"
          />
          <span className="pb-1 text-body text-muted">{transaction?.currency}</span>
        </div>
      </Field>
      <div className="mt-3">
        <Field label="Açıklama">
          <Input value={title} onChange={setTitle} ariaLabel="Açıklama" />
        </Field>
      </div>
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
      <div className="mt-3 flex items-end justify-between gap-3">
        <Field label="Tarih">
          <Input type="date" value={day} onChange={setDay} ariaLabel="Tarih" />
        </Field>
        <Chip tone={transaction?.kind === "income" ? "ok" : "neutral"}>
          {transaction?.kind === "income" ? "Gelir" : "Gider"}
        </Chip>
      </div>
    </Modal>
  );
}
