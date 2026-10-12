import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CalendarClock, CalendarDays, Plus, Repeat, Tag, X } from "lucide-react";
import { Button, Checkbox, Input, cx, useToast } from "@/core/ui";
import { createTask, invalidateTaskWrite, readPlanTodayPreference, writePlanTodayPreference } from "@/core/tasks";
import { localDateKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { PRIORITIES, RECURRENCES } from "./priority";

/**
 * Gorev ekleme.
 *
 * Kapaliyken tek satir; yazmaya baslayinca detaylar aciliyor. Boylece
 * "hizlica bir sey yaz" yolu tek tikla kalirken tarih/oncelik/etiket/rutin
 * hala ayni yerden verilebiliyor -- ayri bir "gelismis" ekran yok.
 */
export function TodoComposer({
  onCreated,
  defaultPlanDay,
  defaultRecurring = false,
}: {
  onCreated?: () => void;
  defaultPlanDay?: string;
  defaultRecurring?: boolean;
}) {
  const [title, setTitle] = useState("");
  const [open, setOpen] = useState(false);
  const [priority, setPriority] = useState(2);
  const [due, setDue] = useState("");
  const [recur, setRecur] = useState(defaultRecurring ? "weekly" : "");
  const [plannedDay, setPlannedDay] = useState(defaultPlanDay ?? "");
  const [tags, setTags] = useState<string[]>([]);
  const [tagDraft, setTagDraft] = useState("");
  // Varsayilan KAPALI ama son secim hatirlanir: her zaman bugune alan kullanici
  // bir kez isaretler, tercih kalir; istemeyen hic etkilenmez.
  const [planToday, setPlanToday] = useState<boolean>(() => readPlanTodayPreference());
  const online = useOnline();
  const toast = useToast();

  function togglePlan(checked: boolean) {
    setPlanToday(checked);
    writePlanTodayPreference(checked);
  }

  function reset() {
    setTitle("");
    setPriority(2);
    setDue("");
    setRecur(defaultRecurring ? "weekly" : "");
    setPlannedDay(defaultPlanDay ?? "");
    setTags([]);
    setTagDraft("");
    setOpen(false);
  }

  const create = useMutation({
    mutationFn: () =>
      createTask({
        title,
        priority,
        // datetime-local yerel saat verir; ISO'ya cevirirken saat dilimi korunur.
        due_at: due ? new Date(due).toISOString() : undefined,
        recur: recur || undefined,
        tags,
        // Istanbul gunu -- agenda'nin SORDUGU helper'dan (lib/date.ts::localDateKey).
        // Aksi halde gorev panelin gostermedigi bir gune planlanir. due_at degil:
        // plan = "bugune al", teslim tarihi ayri kavramdir. Işaretli degilken alan
        // gövdede HIC olmaz (backend "plan yok"u boyle ayirt eder).
        plan_day: plannedDay || (planToday ? localDateKey(new Date()) : undefined),
      }),
    onSuccess: () => {
      reset();
      invalidateTaskWrite();
      onCreated?.();
    },
    onError: () => toast.push("Görev eklenemedi.", { tone: "danger" }),
  });

  function addTag() {
    const clean = tagDraft.trim().replace(/^#/, "");
    if (clean && !tags.includes(clean)) setTags((current) => [...current, clean]);
    setTagDraft("");
  }

  return (
    <form
      className="rounded-card border border-subtle bg-surface"
      onSubmit={(event) => {
        event.preventDefault();
        if (title.trim() && online) create.mutate();
      }}
    >
      <div className="flex items-center gap-2.5 px-3.5 py-2.5">
        <Plus size={16} className="shrink-0 text-icon" />
        <div className="min-w-0 flex-1" onFocusCapture={() => setOpen(true)}>
          <Input
            value={title}
            onChange={setTitle}
            placeholder="Ne yapılacak?"
            ariaLabel="Görev başlığı"
            className="w-full bg-transparent"
          />
        </div>
        {(open || title) && (
          <Button type="submit" variant="primary" size="sm" disabled={!online || !title.trim() || create.isPending}>
            Ekle
          </Button>
        )}
      </div>

      {open && (
        <div className="stack-y-3 border-t border-subtle px-3.5 py-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="mr-1 text-meta text-muted">Öncelik</span>
            {PRIORITIES.map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => setPriority(item.value)}
                aria-pressed={priority === item.value}
                className={cx(
                  "flex items-center gap-1.5 rounded-control border px-2.5 py-1 text-meta transition",
                  priority === item.value
                    ? "border-strong bg-surface-sunken text-primary"
                    : "border-subtle text-muted hover:border-strong hover:text-primary",
                )}
              >
                <span className={cx("h-2 w-2 rounded-full", item.dot)} />
                {item.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="mr-1 flex items-center gap-1 text-meta text-muted">
              <Repeat size={12} /> Tekrar
            </span>
            {RECURRENCES.map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => setRecur(item.value)}
                aria-pressed={recur === item.value}
                className={cx(
                  "rounded-control border px-2.5 py-1 text-meta transition",
                  recur === item.value
                    ? "border-accent-border bg-accent-surface text-accent"
                    : "border-subtle text-muted hover:border-strong hover:text-primary",
                )}
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="mr-1 flex items-center gap-1 text-meta text-muted">
              <CalendarClock size={12} /> Bugün
            </span>
            <Checkbox checked={planToday} onChange={togglePlan} label="bugüne al" />
          </div>

          <label className="block text-meta text-muted">
            Planlanan gün
            <Input type="date" value={plannedDay} onChange={setPlannedDay} className="mt-1 w-full sm:w-48" />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 flex items-center gap-1 text-meta text-muted">
                <CalendarDays size={12} /> Son tarih
              </span>
              <Input type="datetime-local" value={due} onChange={setDue} className="w-full" />
            </label>

            <div>
              <span className="mb-1 flex items-center gap-1 text-meta text-muted">
                <Tag size={12} /> Etiketler
              </span>
              <div className="flex flex-wrap items-center gap-1.5">
                {tags.map((tag) => (
                  <span
                    key={tag}
                    className="flex items-center gap-1 rounded-control border border-accent-border bg-accent-surface px-2 py-1 text-meta text-accent"
                  >
                    #{tag}
                    <button
                      type="button"
                      onClick={() => setTags((c) => c.filter((t) => t !== tag))}
                      aria-label={`${tag} etiketini kaldır`}
                      className="hover:opacity-70"
                    >
                      <X size={11} />
                    </button>
                  </span>
                ))}
                <Input
                  value={tagDraft}
                  onChange={setTagDraft}
                  onKeyDown={(event) => {
                    // Enter formu gondermesin: burada etiket ekliyor.
                    if (event.key === "Enter" || event.key === ",") {
                      event.preventDefault();
                      addTag();
                    }
                    if (event.key === "Backspace" && !tagDraft) setTags((c) => c.slice(0, -1));
                  }}
                  onBlur={addTag}
                  placeholder="etiket ekle"
                  ariaLabel="Etiket"
                  className="min-w-24 flex-1"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <Button size="sm" variant="ghost" onClick={reset}>
              Kapat
            </Button>
          </div>
        </div>
      )}
    </form>
  );
}
