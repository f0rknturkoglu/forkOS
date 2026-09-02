import { useMemo } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, CheckCircle2, Moon, Sun, Sunrise, Sunset } from "lucide-react";
import { api, qs } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { appTimeParts, appWeekStartKey, isSameAppDay, keyToUtc, localDateKey, todayKey, tomorrowKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { Button, Section, cx, useToast } from "@/core/ui";
import type { ActivityEvent, PlanSlot, TodayAgenda, Todo } from "@/core/types";
import { navigate } from "@/app/router";

/**
 * Gunluk ritim orkestratoru (Faz 25).
 *
 * Sabah/gun icinde: gunun sayisal durumu + kritik uyari.
 * Aksam: gunluk degerlendirme durumu + acik planli gorevleri yarina tasi.
 *
 * Orkestrasyon yalnizca Today'de; todo/review/pomodoro is mantigi YENIDEN
 * YAZILMAZ -- hepsi mevcut endpoint/event'lerden turetilir. Yeni tablo
 * yok; kullanici kapatmak isterse Faz 19 widget gizleme yeterli.
 */
export function DailyRhythmWidget() {
  const online = useOnline();
  const toast = useToast();
  const today = todayKey();
  const tomorrow = tomorrowKey();
  const now = new Date();
  const { hour } = appTimeParts(now);
  const phase = hour >= 18 || hour < 4 ? "evening" : hour < 12 ? "morning" : "afternoon";

  const { data: slots = [] } = useQuery({
    queryKey: ["plan", today],
    queryFn: () => api.get<PlanSlot[]>(`/plan${qs({ week: today })}`),
  });
  const { data: events = [] } = useQuery({
    queryKey: ["activity", "review-check"],
    queryFn: () => api.get<ActivityEvent[]>("/activity?limit=40&verbs=review.completed"),
  });
  const { data: agenda } = useQuery({
    queryKey: ["today-agenda", today],
    queryFn: () => api.get<TodayAgenda>(`/today/agenda?day=${today}`),
  });
  const { data: weeklyReviews = [] } = useQuery({
    queryKey: ["reviews", "weekly"],
    queryFn: () => api.get<{ period_start: string }[]>("/reviews?kind=weekly&limit=5"),
  });
  const { data: todos = [] } = useQuery({
    queryKey: ["todos", "rhythm"],
    queryFn: () => api.get<Todo[]>("/todos?limit=200"),
  });

  const todaySlots = useMemo(
    () => slots.filter((slot) => slot.day === today).sort((a, b) => (a.start_min ?? 999) - (b.start_min ?? 999)),
    [slots, today],
  );
  const openTodoIds = useMemo(
    () => new Set(todos.filter((todo) => todo.status === "open" || todo.status === "doing").map((todo) => todo.id)),
    [todos],
  );
  const plannedTodos = todaySlots.filter((slot) => slot.entity_type === "todo" && openTodoIds.has(slot.entity_id));
  const overdue = todos.filter((todo) => todo.due_at && localDateKey(new Date(todo.due_at)) < today).length;
  const reviewDone = events.some((event) => isSameAppDay(new Date(event.occurred_at), new Date()));
  const weekStart = appWeekStartKey(now);
  const weekDay = keyToUtc(today).getUTCDay();
  const weeklyReviewDue =
    (weekDay === 0 || weekDay === 1) && !weeklyReviews.some((review) => review.period_start === weekStart);
  const conflictCount = useMemo(() => {
    const calendarRows = (agenda?.timed ?? []).filter(
      (row) => row.kind === "calendar" && row.starts_at && localDateKey(new Date(row.starts_at)) === today,
    );
    return plannedTodos.reduce((count, slot) => {
      if (slot.start_min == null) return count;
      const slotEnd = slot.start_min + (slot.duration_min ?? 30);
      return (
        count +
        calendarRows.filter((row) => {
          const startsAt = new Date(row.starts_at!);
          const parts = appTimeParts(startsAt);
          const eventStart = parts.hour * 60 + parts.minute;
          const eventEnd = eventStart + (row.duration_min ?? 30);
          return slot.start_min! < eventEnd && eventStart < slotEnd;
        }).length
      );
    }, 0);
  }, [agenda, plannedTodos, today]);
  const carryOver = useMutation({
    // Tek istek, tek transaction (Faz 33): kismi tasima yok.
    mutationFn: () => api.post<{ moved: number }>("/plan/carry-over", { day: today, target: tomorrow }),
    onSuccess: (result) => {
      invalidateAfter("plan.write");
      toast.push(`${result.moved} görev yarına taşındı.`, { tone: "ok" });
    },
    onError: () => toast.push("Taşıma başarısız — hiçbir slot değişmedi.", { tone: "danger" }),
  });

  const phaseIcon = phase === "morning" ? Sunrise : phase === "evening" ? Sunset : Sun;
  const PhaseIcon = phaseIcon;
  const phaseLabel = phase === "morning" ? "Sabah" : phase === "afternoon" ? "Gün içinde" : "Akşam";

  return (
    <Section title="Gün özeti" hint={phaseLabel}>
      <div className="space-y-3">
        <p className="flex items-center gap-1.5 text-meta text-muted">
          <PhaseIcon size={13} className="shrink-0 text-icon" />
          {phase === "morning" && (
            <>
              Bugün <strong className="font-medium text-primary">{plannedTodos.length}</strong> planlı ·{" "}
              <strong className="font-medium text-primary">{overdue}</strong> geciken
            </>
          )}
          {phase === "afternoon" && (
            <>
              Bugün <strong className="font-medium text-primary">{plannedTodos.length}</strong> planlı ·{" "}
              <strong className="font-medium text-primary">{overdue}</strong> geciken
            </>
          )}
          {phase === "evening" && (
            <>
              {reviewDone ? (
                <span className="flex items-center gap-1 text-ok">
                  <CheckCircle2 size={13} /> Günü değerlendirdin
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <Moon size={13} /> Gün sonu değerlendirmesi bekliyor
                </span>
              )}
            </>
          )}
        </p>

        {weeklyReviewDue && (
          <Button size="sm" variant="secondary" disabled={!online} onClick={() => navigate("/review/weekly")}>
            <ArrowRight size={13} /> Haftalık değerlendirme bekliyor
          </Button>
        )}

        {conflictCount > 0 && (
          <p className="flex items-center gap-1.5 text-meta text-warn">
            <AlertTriangle size={13} /> {conflictCount} takvim çakışması
          </p>
        )}

        {phase === "evening" && !reviewDone && (
          <Button size="sm" variant="secondary" disabled={!online} onClick={() => navigate("/review/daily")}>
            <ArrowRight size={13} /> Değerlendirmeye git
          </Button>
        )}

        {phase === "evening" && plannedTodos.length > 0 && (
          <div className="flex items-center justify-between gap-2 rounded-card border border-subtle px-3 py-2">
            <span className="text-meta text-muted">{plannedTodos.length} planlı görev açık</span>
            <Button size="sm" disabled={!online || carryOver.isPending} onClick={() => carryOver.mutate()}>
              {carryOver.isPending ? "Taşınıyor…" : "Yarına taşı"}
            </Button>
          </div>
        )}

        {phase !== "evening" && plannedTodos.length === 0 && (
          <p className={cx("text-meta", overdue > 0 ? "text-warn" : "text-muted")}>
            Bugün için planlı görev yok{overdue > 0 ? ` — ${overdue} geciken görev var` : ""}.
          </p>
        )}
      </div>
    </Section>
  );
}
