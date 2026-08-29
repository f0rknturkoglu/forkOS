import { useMemo } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, Coffee, Moon, PlayCircle, Sun, Sunrise, Sunset } from "lucide-react";
import { api, qs } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { appTimeParts, isSameAppDay, localDateKey, todayKey, tomorrowKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { Button, Section, cx, useToast } from "@/core/ui";
import type { ActivityEvent, BookmarkStats, PlanSlot, PomodoroSession, Todo } from "@/core/types";
import { navigate } from "@/app/router";

/**
 * Gunluk ritim orkestratoru (Faz 25).
 *
 * Sabah: gelen kutusu + bugunun planli isleri (ilk 3) + ilk odak.
 * Gun icinde: siradaki planli is + aktif pomodoro + gecikenler.
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
  const { hour } = appTimeParts(new Date());
  const phase = hour >= 18 || hour < 4 ? "evening" : hour < 12 ? "morning" : "afternoon";

  const { data: stats = null } = useQuery({
    queryKey: ["bookmark-stats"],
    queryFn: () => api.get<BookmarkStats>("/bookmarks/stats"),
  });
  const { data: slots = [] } = useQuery({
    queryKey: ["plan", today],
    queryFn: () => api.get<PlanSlot[]>(`/plan${qs({ week: today })}`),
  });
  const { data: active = null } = useQuery({
    queryKey: ["pomodoro-active"],
    queryFn: () => api.get<PomodoroSession | null>("/pomodoro/active"),
  });
  const { data: events = [] } = useQuery({
    queryKey: ["activity", "review-check"],
    queryFn: () => api.get<ActivityEvent[]>("/activity?limit=40&verbs=review.completed"),
  });
  const { data: todos = [] } = useQuery({
    queryKey: ["todos", "rhythm"],
    queryFn: () => api.get<Todo[]>("/todos?status=open&limit=200"),
  });

  const todaySlots = useMemo(
    () => slots.filter((slot) => slot.day === today).sort((a, b) => (a.start_min ?? 999) - (b.start_min ?? 999)),
    [slots, today],
  );
  const plannedTodos = todaySlots.filter((slot) => slot.entity_type === "todo");
  const firstThree = plannedTodos.slice(0, 3);
  const overdue = todos.filter((todo) => todo.due_at && localDateKey(new Date(todo.due_at)) < today).length;
  const reviewDone = events.some((event) => isSameAppDay(new Date(event.occurred_at), new Date()));
  const inboxCount = stats?.inbox ?? 0;

  const carryOver = useMutation({
    // Tek istek, tek transaction (Faz 33): kismi tasima yok.
    mutationFn: () => api.post<{ moved: number }>("/plan/carry-over", { day: today, target: tomorrow }),
    onSuccess: (result) => {
      invalidateAfter("plan.write");
      toast.push(`${result.moved} görev yarına taşındı.`, { tone: "ok" });
    },
    onError: () => toast.push("Taşıma başarısız — hiçbir slot değişmedi.", { tone: "danger" }),
  });

  const firstFocus = plannedTodos.find((slot) => slot.start_min != null) ?? plannedTodos[0];
  const nowMin = hour * 60 + appTimeParts(new Date()).minute;
  const nextUp =
    plannedTodos.find((slot) => slot.start_min != null && slot.start_min >= nowMin) ??
    plannedTodos.find((slot) => slot.start_min == null) ??
    firstFocus;

  const phaseIcon = phase === "morning" ? Sunrise : phase === "evening" ? Sunset : Sun;
  const PhaseIcon = phaseIcon;
  const phaseLabel = phase === "morning" ? "Sabah" : phase === "afternoon" ? "Gün içinde" : "Akşam";

  return (
    <Section title="Günün ritmi" hint={phaseLabel}>
      <div className="space-y-3">
        <p className="flex items-center gap-1.5 text-meta text-muted">
          <PhaseIcon size={13} className="shrink-0 text-icon" />
          {phase === "morning" && (
            <>
              Gelen kutusunda <strong className="font-medium text-primary">{inboxCount}</strong> · bugün{" "}
              <strong className="font-medium text-primary">{plannedTodos.length}</strong> planlı görev
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

        {phase !== "evening" && firstThree.length > 0 && (
          <ul className="space-y-1">
            {firstThree.map((slot) => (
              <li key={slot.id} className="flex items-center gap-2 text-meta">
                <span className="numeral w-8 shrink-0 text-right text-muted">
                  {slot.start_min != null
                    ? `${String(Math.floor(slot.start_min / 60)).padStart(2, "0")}:${String(
                        slot.start_min % 60,
                      ).padStart(2, "0")}`
                    : "—"}
                </span>
                <a
                  href={`#${slot.entity_type === "todo" ? "/todos?focus=" + slot.entity_id : "/today"}`}
                  className="min-w-0 flex-1 truncate text-primary hover:text-accent"
                >
                  {slot.title}
                </a>
              </li>
            ))}
          </ul>
        )}

        {phase === "morning" && firstFocus && (
          <Button size="sm" variant="primary" disabled={!online} onClick={() => navigate("/pomodoro")}>
            <PlayCircle size={13} /> İlk odağı başlat
          </Button>
        )}

        {phase === "afternoon" && active && (
          <Button size="sm" variant="primary" disabled={!online} onClick={() => navigate("/pomodoro")}>
            <Coffee size={13} /> Odak devam ediyor — aç
          </Button>
        )}

        {phase === "afternoon" && nextUp && (
          <p className="text-meta text-muted">
            Sıradaki: <span className="text-primary">{nextUp.title}</span>
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
