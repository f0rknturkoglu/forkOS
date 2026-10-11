import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, CheckCircle2, Moon, Sun, Sunrise, Sunset } from "lucide-react";
import { api, qs } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { todayKey, tomorrowKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { Button, Section, cx, useToast } from "@/core/ui";
import type { ActivityEvent, PlanSlot, TodayAgenda, Todo } from "@/core/types";
import { navigate } from "@/app/router";
import { deriveTodayState } from "./todayState";

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
    // Ajanda ile ayni sorgu anahtari: widget acikken ikinci bir tam todo
    // istegi atilmaz.
    queryKey: ["todos", "today-open"],
    queryFn: () => api.get<Todo[]>("/todos?limit=300"),
  });

  const { phase, phaseLabel, plannedTodos, overdue, reviewDone, weeklyReviewDue, conflictCount } = deriveTodayState({
    day: today,
    now,
    slots,
    todos,
    agenda,
    reviewEvents: events,
    weeklyReviews,
  });
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

  return (
    <Section title="Gün özeti" hint={phaseLabel}>
      <div className="stack-y-3">
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
