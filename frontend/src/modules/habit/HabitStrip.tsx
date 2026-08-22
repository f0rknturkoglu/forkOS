import { useMutation } from "@tanstack/react-query";
import { api } from "@/core/api";
import { cx } from "@/core/ui";
import { useInvalidate, useOnline } from "@/lib/hooks";

/**
 * Bir aliskanligin son N gunu -- emek haritasiyla ayni dilde kareler.
 *
 * Onceki hali 56 gunu 7 satira dizen dikey bir izgaraydi; hangi karenin
 * hangi gun oldugu okunamiyordu. Burada tek satir, saga dogru bugune
 * ilerleyen kareler var ve her kare tiklanabilir (gecmise isaretleme).
 */
export function HabitStrip({
  habitId, done, days = 28, size = "md",
}: {
  habitId: string;
  /** "YYYY-MM-DD" -> isaretli mi. */
  done: Set<string>;
  days?: number;
  size?: "sm" | "md";
}) {
  const online = useOnline();
  const invalidate = useInvalidate();

  const check = useMutation({
    mutationFn: ({ day, next }: { day: string; next: boolean }) =>
      api.post(`/habits/${habitId}/check`, { day, done: next }),
    onSuccess: () => invalidate("habits", "habits-grid", "activity"),
  });

  const today = localDay();
  const cells = Array.from({ length: days }, (_, index) => {
    const date = new Date();
    date.setDate(date.getDate() - (days - index - 1));
    return localDay(date);
  });

  const box = size === "sm" ? "h-2.5 w-2.5" : "h-3.5 w-3.5";

  return (
    <div className="flex flex-wrap gap-1">
      {cells.map((day) => {
        const checked = done.has(day);
        const isToday = day === today;
        return (
          <button
            key={day}
            type="button"
            disabled={!online || check.isPending}
            onClick={() => check.mutate({ day, next: !checked })}
            title={`${new Date(day).toLocaleDateString("tr-TR", {
              day: "numeric", month: "long",
            })}${checked ? " · yapıldı" : ""}`}
            aria-label={`${day} ${checked ? "yapıldı" : "yapılmadı"}`}
            className={cx(
              box,
              "rounded-[3px] transition",
              checked ? "bg-heat-4 hover:bg-heat-3" : "bg-heat-0 hover:bg-heat-1",
              isToday && "ring-2 ring-accent ring-offset-1 ring-offset-surface",
              !online && "cursor-not-allowed",
            )}
          />
        );
      })}
    </div>
  );
}

/** YEREL gunun ISO tarihi -- toISOString() UTC verir, TR'de gun kayar. */
export function localDay(date = new Date()): string {
  const copy = new Date(date);
  copy.setMinutes(copy.getMinutes() - copy.getTimezoneOffset());
  return copy.toISOString().slice(0, 10);
}
