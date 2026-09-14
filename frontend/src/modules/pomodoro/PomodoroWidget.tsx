import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Maximize2, Pause, Play, Plus, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { Button, IconButton, Input, RowList, Section, cx, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { PomodoroSession, PomodoroStats } from "@/core/types";
import { BREAK_MIN, FOCUS_MIN, clock, remaining } from "./time";
import { FocusMode } from "./FocusMode";
import { openPomodoro } from "./dock";

/**
 * Bugun panelinden pomodoro'nun TAM kontrolu: baslat, duraklat, tamamla,
 * yarida kes, elle isle, sil. Panelden Pomodoro sayfasina gitmek gerekmiyor.
 */
export function PomodoroWidget() {
  const [now, setNow] = useState(Date.now());
  const [focusMode, setFocusMode] = useState(false);
  const [adding, setAdding] = useState(false);
  const online = useOnline();
  const toast = useToast();

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const { data: active } = useQuery({
    queryKey: ["pomodoro-active"],
    queryFn: () => api.get<PomodoroSession | null>("/pomodoro/active"),
    refetchInterval: 30_000,
  });
  const { data: stats } = useQuery({
    queryKey: ["pomodoro-stats", "today"],
    queryFn: () => api.get<PomodoroStats>("/pomodoro/stats?range=day"),
  });
  const { data: sessions = [] } = useQuery({
    queryKey: ["pomodoro-sessions"],
    queryFn: () => api.get<PomodoroSession[]>("/pomodoro/sessions?limit=4"),
  });

  const refresh = () => invalidateAfter("pomodoro.write");
  const refreshTimeline = () => invalidateAfter("pomodoro.write");

  const start = useMutation({
    mutationFn: (kind: "focus" | "short_break") =>
      api.post("/pomodoro/start", {
        planned_min: kind === "focus" ? FOCUS_MIN : BREAK_MIN,
        kind,
      }),
    onSuccess: refresh,
    onError: () => toast.push("Başlatılamadı — aktif bir seans olabilir.", { tone: "danger" }),
  });
  const stop = useMutation({
    mutationFn: (interrupted: boolean) => api.post(`/pomodoro/${active?.id}/stop`, { interrupted }),
    onSuccess: refreshTimeline,
  });
  const togglePause = useMutation({
    mutationFn: () => api.post(`/pomodoro/${active?.id}/${active?.paused_at ? "resume" : "pause"}`),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/pomodoro/${id}`),
    onSuccess: () => {
      refresh();
      toast.push("Seans silindi", { tone: "ok" });
    },
  });

  const left = remaining(active, now);
  const paused = Boolean(active?.paused_at);

  return (
    <>
      <Section
        title="Odak"
        action={
          <span className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setAdding((v) => !v)}
              className="flex items-center gap-1 text-meta text-accent hover:underline"
            >
              <Plus size={13} /> {adding ? "kapat" : "elle"}
            </button>
            <button type="button" onClick={() => openPomodoro()} className="text-meta text-muted hover:text-primary">
              aç →
            </button>
          </span>
        }
      >
        {adding && (
          <QuickManual
            onDone={() => {
              setAdding(false);
              refresh();
            }}
          />
        )}

        {active ? (
          <div>
            <button
              type="button"
              onClick={() => setFocusMode(true)}
              title="Odak moduna gir"
              className="group block w-full text-left"
            >
              <span className="flex items-baseline gap-2">
                <span
                  className={cx(
                    "numeral text-display leading-none tabular-nums transition-colors",
                    paused ? "text-muted" : "text-primary group-hover:text-accent",
                  )}
                >
                  {clock(left)}
                </span>
                <Maximize2 size={13} className="text-icon transition-colors group-hover:text-accent" />
              </span>
              <span className="mt-1 block truncate text-meta text-muted">
                {paused ? "duraklatıldı" : active.topic || active.context_title || "Odak"}
              </span>
            </button>

            <div className="mt-3 flex flex-wrap gap-1.5">
              <Button size="sm" disabled={!online || togglePause.isPending} onClick={() => togglePause.mutate()}>
                {paused ? (
                  <>
                    <Play size={13} /> devam
                  </>
                ) : (
                  <>
                    <Pause size={13} /> duraklat
                  </>
                )}
              </Button>
              <Button size="sm" disabled={!online} onClick={() => stop.mutate(false)}>
                tamamla
              </Button>
              <Button size="sm" variant="danger" disabled={!online} onClick={() => stop.mutate(true)}>
                kes
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            <Button
              size="sm"
              variant="primary"
              disabled={!online || start.isPending}
              onClick={() => start.mutate("focus")}
            >
              {FOCUS_MIN} dk odak
            </Button>
            <Button size="sm" disabled={!online || start.isPending} onClick={() => start.mutate("short_break")}>
              {BREAK_MIN} dk mola
            </Button>
          </div>
        )}

        <p className="mt-3 border-t border-subtle pt-2 text-meta text-muted">
          Bugün {stats?.minutes ?? 0} dk · {stats?.sessions ?? 0} seans
        </p>

        {sessions.length > 0 && (
          <RowList as="ul" className="mt-1">
            {sessions.map((item) => (
              <li key={item.id} className="group flex items-center gap-2 py-1.5">
                <span className={cx("h-1.5 w-1.5 shrink-0 rounded-full", item.interrupted ? "bg-warn" : "bg-ok")} />
                <span className="min-w-0 flex-1 truncate text-meta text-secondary">
                  {item.topic || item.context_title || "Odak"}
                </span>
                <span className="shrink-0 text-meta text-muted">{item.actual_min ?? 0} dk</span>
                <IconButton
                  title="Seansı sil"
                  tone="danger"
                  disabled={!online || remove.isPending}
                  onClick={() => remove.mutate(item.id)}
                  className="h-6 w-6 opacity-0 transition group-hover:opacity-100"
                >
                  <Trash2 size={12} />
                </IconButton>
              </li>
            ))}
          </RowList>
        )}
      </Section>

      {focusMode && active && <FocusMode onClose={() => setFocusMode(false)} />}
    </>
  );
}

/** Panelden hizli elle isleme: baslangic + sure yeter, gerisi Pomodoro sayfasinda. */
function QuickManual({ onDone }: { onDone: () => void }) {
  const [when, setWhen] = useState(() => {
    const d = new Date(Date.now() - FOCUS_MIN * 60_000);
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  });
  const [minutes, setMinutes] = useState(FOCUS_MIN);
  const [topic, setTopic] = useState("");
  const online = useOnline();
  const toast = useToast();

  const add = useMutation({
    mutationFn: () =>
      api.post("/pomodoro", {
        started_at: new Date(when).toISOString(),
        minutes,
        topic: topic || undefined,
      }),
    onSuccess: () => {
      toast.push("Seans işlendi", { tone: "ok" });
      onDone();
    },
    onError: () => toast.push("İşlenemedi — tarih gelecekte olabilir.", { tone: "danger" }),
  });

  return (
    <form
      className="mb-3 space-y-2 border-b border-subtle pb-3"
      onSubmit={(event) => {
        event.preventDefault();
        add.mutate();
      }}
    >
      <Input type="datetime-local" value={when} onChange={setWhen} className="w-full" ariaLabel="Başlangıç" />
      <div className="flex gap-2">
        <Input
          type="number"
          value={String(minutes)}
          onChange={(value) => setMinutes(Math.max(1, Math.min(600, Number(value) || FOCUS_MIN)))}
          className="w-20"
          ariaLabel="Süre (dakika)"
        />
        <Input value={topic} onChange={setTopic} placeholder="Konu" className="min-w-0 flex-1" />
      </div>
      <Button type="submit" size="sm" variant="primary" disabled={!online || add.isPending}>
        İşle
      </Button>
    </form>
  );
}
