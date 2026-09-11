import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, Maximize2, Pause, Play, Timer, X } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import type { PomodoroSession, PomodoroStats } from "@/core/types";
import { Button, Field, IconButton, Input, cx, useToast } from "@/core/ui";
import { MediaSessionTransfer } from "@/modules/media/MediaSessionTransfer";
import { useOnline } from "@/lib/hooks";
import { ContextChip, ContextPicker } from "./ContextPicker";
import { FocusMode } from "./FocusMode";
import { POMODORO_OPEN_EVENT, type PomodoroOpenRequest } from "./dock";
import { BREAK_MIN, FOCUS_MIN, clock, remaining } from "./time";

const PRESETS = [25, FOCUS_MIN] as const;

/**
 * Uygulama kabugunda tek kez render edilen global Pomodoro.
 * Sayfa degisse de aktif seans ve acik panel ayni React agacinda kalir.
 */
export function PomodoroDock() {
  const [open, setOpen] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [minutes, setMinutes] = useState(FOCUS_MIN);
  const [topic, setTopic] = useState("");
  const [context, setContext] = useState("");
  const online = useOnline();
  const toast = useToast();

  useEffect(() => {
    const onOpen = (event: Event) => {
      const detail = (event as CustomEvent<PomodoroOpenRequest>).detail ?? {};
      if (detail.topic !== undefined) setTopic(detail.topic);
      if (detail.context !== undefined) setContext(detail.context);
      setOpen(true);
    };
    window.addEventListener(POMODORO_OPEN_EVENT, onOpen);
    return () => window.removeEventListener(POMODORO_OPEN_EVENT, onOpen);
  }, []);

  const { data: active = null } = useQuery({
    queryKey: ["pomodoro-active"],
    queryFn: () => api.get<PomodoroSession | null>("/pomodoro/active"),
    refetchInterval: 30_000,
  });
  // Seans bittiğinde medya bağlamlıysa süreyi tüketime aktarmayı öneririz.
  const [finished, setFinished] = useState<PomodoroSession | null>(null);
  const { data: stats } = useQuery({
    queryKey: ["pomodoro-stats", "today"],
    queryFn: () => api.get<PomodoroStats>("/pomodoro/stats?range=day"),
  });

  // Global yuzey her sayfada render ediliyor. Aktif seans yokken tum
  // uygulamayi saniyede bir yeniden render ettirmemek icin saat yalnizca
  // gercekten akarken calisir.
  useEffect(() => {
    setNow(Date.now());
    if (!active || active.paused_at) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [active?.id, active?.paused_at]);

  const refresh = () => invalidateAfter("pomodoro.write");
  const start = useMutation({
    mutationFn: (kind: "focus" | "short_break") =>
      api.post("/pomodoro/start", {
        planned_min: kind === "focus" ? minutes : BREAK_MIN,
        kind,
        topic: kind === "focus" ? topic.trim() || undefined : undefined,
        context_entity_id: kind === "focus" ? context || undefined : undefined,
      }),
    onSuccess: refresh,
    onError: () => toast.push("Başlatılamadı — aktif bir seans olabilir.", { tone: "danger" }),
  });
  const stop = useMutation({
    mutationFn: (interrupted: boolean) => api.post(`/pomodoro/${active?.id}/stop`, { interrupted }),
    onSuccess: (_data, interrupted) => {
      // Aktif seans refetch'te temizlenmeden yakala: medya bağlamlı biten seans
      // tüketime aktarılabilir (Faz 8 köprüsü).
      const ended = active;
      refresh();
      if (!interrupted && ended?.context_type === "media_item" && ended.context_entity_id) {
        setFinished(ended);
      }
    },
  });
  const togglePause = useMutation({
    mutationFn: () => api.post(`/pomodoro/${active?.id}/${active?.paused_at ? "resume" : "pause"}`),
    onSuccess: refresh,
  });

  const left = remaining(active, now);
  const paused = Boolean(active?.paused_at);
  const totalSeconds = (active?.planned_min ?? minutes) * 60;
  const progress = totalSeconds > 0 ? Math.min(100, Math.max(0, ((totalSeconds - left) / totalSeconds) * 100)) : 0;

  useEffect(() => {
    if (active && !paused && left === 0 && !stop.isPending && online) stop.mutate(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [left, active?.id, paused, online]);

  return (
    <>
      {open && (
        <aside
          role="dialog"
          aria-label="Pomodoro seçenekleri"
          className="fixed bottom-20 left-4 right-4 z-popover max-h-screen overflow-y-auto rounded-overlay border border-strong bg-surface shadow-overlay sm:left-auto sm:right-5 sm:w-96"
        >
          <header className="flex items-center gap-3 border-b border-subtle px-4 py-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-control bg-accent-surface text-accent">
              <Timer size={16} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-body font-medium text-primary">Pomodoro</p>
              <p className="truncate text-meta text-muted">
                {active ? (paused ? "Duraklatıldı" : "Odak devam ediyor") : "Yeni odak bloğu"}
              </p>
            </div>
            <a href="#/pomodoro" className="text-meta text-muted hover:text-primary">
              geçmiş
            </a>
            <IconButton title="Pomodoro panelini küçült" onClick={() => setOpen(false)}>
              <X size={14} />
            </IconButton>
          </header>

          {active ? (
            <div className="space-y-4 p-4">
              <div>
                <div className="flex items-end justify-between gap-3">
                  <div className={cx("numeral text-display tabular-nums", paused ? "text-muted" : "text-primary")}>
                    {clock(left)}
                  </div>
                  <span className="text-meta text-muted">{active.planned_min} dk</span>
                </div>
                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-sunken">
                  <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${progress}%` }} />
                </div>
                <div className="mt-2 flex min-w-0 items-center gap-1.5 text-meta text-muted">
                  <span className="truncate">{active.topic || active.context_title || "Bağımsız odak"}</span>
                  <ContextChip type={active.context_type} />
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="primary" disabled={!online} onClick={() => setFocusMode(true)}>
                  <Maximize2 size={13} /> odak modu
                </Button>
                <Button size="sm" disabled={!online || togglePause.isPending} onClick={() => togglePause.mutate()}>
                  {paused ? <Play size={13} /> : <Pause size={13} />}
                  {paused ? "devam" : "duraklat"}
                </Button>
                <Button size="sm" disabled={!online || stop.isPending} onClick={() => stop.mutate(false)}>
                  <Check size={13} /> tamamla
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  disabled={!online || stop.isPending}
                  onClick={() => stop.mutate(true)}
                >
                  yarıda kes
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4 p-4">
              <div>
                <p className="mb-2 text-meta text-secondary">Süre</p>
                <div className="flex flex-wrap items-center gap-2">
                  {PRESETS.map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      aria-pressed={minutes === preset}
                      onClick={() => setMinutes(preset)}
                      className={cx(
                        "rounded-control border px-3 py-1.5 text-meta transition",
                        minutes === preset
                          ? "border-accent-border bg-accent-surface text-accent"
                          : "border-subtle text-muted hover:border-strong hover:text-primary",
                      )}
                    >
                      {preset} dk
                    </button>
                  ))}
                  <Input
                    type="number"
                    value={String(minutes)}
                    onChange={(value) => setMinutes(Math.max(1, Math.min(240, Number(value) || FOCUS_MIN)))}
                    ariaLabel="Özel Pomodoro süresi"
                    className="w-20"
                  />
                </div>
              </div>

              <Field label="Konu">
                <Input value={topic} onChange={setTopic} placeholder="Neye odaklanıyorsun?" className="w-full" />
              </Field>
              <ContextPicker value={context} onChange={setContext} />

              <div className="flex gap-2 border-t border-subtle pt-4">
                <Button
                  variant="primary"
                  className="flex-1"
                  disabled={!online || start.isPending}
                  onClick={() => start.mutate("focus")}
                >
                  <Play size={14} /> {minutes} dk odak
                </Button>
                <Button disabled={!online || start.isPending} onClick={() => start.mutate("short_break")}>
                  {BREAK_MIN} dk mola
                </Button>
              </div>
            </div>
          )}

          <footer className="border-t border-subtle px-4 py-2 text-meta text-muted">
            Bugün {stats?.minutes ?? 0} dk · {stats?.sessions ?? 0} seans
          </footer>
        </aside>
      )}

      <button
        type="button"
        aria-expanded={open}
        aria-label={active ? `Pomodoro ${clock(left)}` : "Pomodoro seçeneklerini aç"}
        onClick={() => setOpen((value) => !value)}
        className={cx(
          "fixed bottom-5 right-5 z-popover flex h-11 items-center gap-2 rounded-full border px-4 shadow-overlay transition",
          active
            ? "border-accent-border bg-accent-surface text-accent hover:brightness-95"
            : "border-strong bg-surface text-secondary hover:bg-surface-hover hover:text-primary",
        )}
      >
        <Timer size={16} />
        <span className="numeral text-body tabular-nums">{active ? clock(left) : "Pomodoro"}</span>
        {active && !paused && <span className="h-1.5 w-1.5 rounded-full bg-ok" aria-hidden />}
      </button>

      {focusMode && active && <FocusMode onClose={() => setFocusMode(false)} />}
      <MediaSessionTransfer session={finished} onClose={() => setFinished(null)} />
    </>
  );
}
