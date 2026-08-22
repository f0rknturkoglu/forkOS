import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, Plus, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import {
  Button, Empty, Field, IconButton, Input, PageFrame, PageHeader, Section, Select, cx, useToast,
} from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import type { Habit, HabitGridEntry } from "@/core/types";
import { useInvalidate, useOnline } from "@/lib/hooks";
import { HabitStrip, localDay } from "./HabitStrip";

/**
 * Aliskanliklar: her biri bir kart, icinde son dort haftanin kareleri.
 *
 * Rozet ve ceza yok; gosterilen tek sey ritim -- bu hafta kac gun, kac gun
 * ust uste, rekor ne. Hedefin altinda kalmak kirmizi yanmaz: hedef bir
 * yon, bir sinav degil.
 */
export function HabitPage() {
  const [adding, setAdding] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const online = useOnline();
  const invalidate = useInvalidate();
  const toast = useToast();

  const { data: habits = [] } = useQuery({
    queryKey: ["habits", showArchived],
    queryFn: () => api.get<Habit[]>(`/habits${showArchived ? "?active=false" : ""}`),
  });
  const { data: grid = [] } = useQuery({
    queryKey: ["habits-grid"],
    queryFn: () => api.get<HabitGridEntry[]>("/habits/grid?weeks=8"),
  });

  const refresh = () =>
    invalidate("habits", "habits-grid", "activity", "review-preview");

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: object }) => api.patch(`/habits/${id}`, body),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/habits/${id}`),
    onSuccess: () => { refresh(); toast.push("Alışkanlık silindi", { tone: "ok" }); },
  });
  const check = useMutation({
    mutationFn: (habit: Habit) =>
      api.post(`/habits/${habit.id}/check`, { day: localDay(), done: !habit.done_today }),
    onSuccess: refresh,
  });

  const doneByHabit = grid.reduce<Record<string, Set<string>>>((acc, entry) => {
    if (entry.done) (acc[entry.habit_id] ??= new Set()).add(entry.day);
    return acc;
  }, {});

  return (
    <PageFrame className="space-y-5">
      <PageHeader
        eyebrow="Takip"
        title="Alışkanlıklar"
        action={
          <Button variant="primary" size="sm" onClick={() => setAdding((v) => !v)} disabled={!online}>
            <Plus size={14} /> {adding ? "vazgeç" : "Yeni"}
          </Button>
        }
      />
      <p className="text-meta text-muted">
        Rozet yok, ceza yok; yalnızca ritim. Karelere tıklayarak geçmiş günleri de işaretleyebilirsin.
      </p>

      {adding && <NewHabit onDone={() => { setAdding(false); refresh(); }} />}

      <div className="flex items-center gap-2">
        <button type="button" onClick={() => setShowArchived((v) => !v)}
          className="text-meta text-muted transition hover:text-primary">
          {showArchived ? "← aktif olanlar" : "bırakılanları göster →"}
        </button>
      </div>

      {habits.length === 0 ? (
        <Empty variant="page" title={showArchived ? "Bırakılan yok" : "Henüz alışkanlık yok"}>
          Küçük başla: “20 dk oku”, “sabah yürüyüşü”. Haftalık hedefi düşük tut.
        </Empty>
      ) : (
        <div className="grid gap-5 lg:grid-cols-2">
          {habits.map((habit) => {
            const done = doneByHabit[habit.id] ?? new Set<string>();
            const reached = habit.week_done >= habit.target_per_week;
            return (
              <Section
                key={habit.id}
                title={habit.title}
                hint={
                  <span className={cx("tabular-nums", reached ? "text-ok" : "text-muted")}>
                    bu hafta {habit.week_done}/{habit.target_per_week}
                  </span>
                }
                action={
                  <span className="flex items-center gap-1">
                    <IconButton
                      title={habit.active ? "Bırak (geçmiş kalır)" : "Yeniden başlat"}
                      disabled={!online}
                      onClick={() => update.mutate({ id: habit.id, body: { active: !habit.active } })}
                    >
                      {habit.active ? <span className="text-[11px]">bırak</span>
                                    : <span className="text-[11px]">geri al</span>}
                    </IconButton>
                    <IconButton title="Sil" tone="danger" disabled={!online}
                      onClick={async () => {
                        const ok = await confirmDialog({
                          title: `"${habit.title}" silinsin mi?`,
                          body: "Tüm geçmişi de gider. Sadece bırakmak istiyorsan “bırak” yeter.",
                          confirmLabel: "Sil",
                          tone: "danger",
                        });
                        if (ok) remove.mutate(habit.id);
                      }}>
                      <Trash2 size={14} />
                    </IconButton>
                  </span>
                }
              >
                <div className="mb-3 flex items-center gap-3">
                  <button
                    type="button"
                    disabled={!online}
                    onClick={() => check.mutate(habit)}
                    aria-label={habit.done_today ? "Bugünü geri al" : "Bugünü işaretle"}
                    className={cx(
                      "flex h-9 shrink-0 items-center gap-2 rounded-control border px-3 text-meta transition",
                      habit.done_today
                        ? "border-ok bg-ok text-canvas"
                        : "border-strong text-secondary hover:border-accent hover:text-accent",
                    )}
                  >
                    <Check size={14} strokeWidth={3} />
                    {habit.done_today ? "bugün yapıldı" : "bugünü işaretle"}
                  </button>

                  <span className="text-meta text-muted">
                    <span className="text-primary">{habit.streak}</span> gün üst üste
                    {habit.best_streak > habit.streak && ` · rekor ${habit.best_streak}`}
                  </span>
                </div>

                <HabitStrip habitId={habit.id} done={done} days={28} />

                <div className="mt-3 border-t border-subtle pt-3">
                  <Field label="Haftalık hedef">
                    <Select
                      value={String(habit.target_per_week)}
                      onChange={(value) =>
                        update.mutate({ id: habit.id, body: { target_per_week: Number(value) } })}
                      disabled={!online}
                      className="w-32"
                      ariaLabel="Haftalık hedef"
                    >
                      {[1, 2, 3, 4, 5, 6, 7].map((value) => (
                        <option key={value} value={value}>{value} gün</option>
                      ))}
                    </Select>
                  </Field>
                </div>
              </Section>
            );
          })}
        </div>
      )}
    </PageFrame>
  );
}

function NewHabit({ onDone }: { onDone: () => void }) {
  const [title, setTitle] = useState("");
  const [target, setTarget] = useState(5);
  const online = useOnline();
  const toast = useToast();

  const create = useMutation({
    mutationFn: () => api.post("/habits", { title: title.trim(), target_per_week: target }),
    onSuccess: onDone,
    onError: () => toast.push("Eklenemedi.", { tone: "danger" }),
  });

  return (
    <Section title="Yeni alışkanlık">
      <form className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-end"
        onSubmit={(event) => { event.preventDefault(); if (title.trim()) create.mutate(); }}>
        <Field label="Ne yapacaksın">
          <Input value={title} onChange={setTitle} placeholder="Örn. 20 dk oku" className="w-full" />
        </Field>
        <Field label="Haftada">
          <Select value={String(target)} onChange={(value) => setTarget(Number(value))}
            className="w-28" ariaLabel="Haftalık hedef">
            {[1, 2, 3, 4, 5, 6, 7].map((value) => (
              <option key={value} value={value}>{value} gün</option>
            ))}
          </Select>
        </Field>
        <Button type="submit" variant="primary" disabled={!online || !title.trim() || create.isPending}>
          Ekle
        </Button>
      </form>
    </Section>
  );
}
