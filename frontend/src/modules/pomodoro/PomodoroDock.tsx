import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, FileText, ListChecks, Maximize2, Pause, Play, Plus, StickyNote, Timer, X } from "lucide-react";
import { api } from "@/core/api";
import { openCapture } from "@/core/CaptureDialog";
import { invalidateAfter } from "@/core/invalidation";
import type { PomodoroSession, PomodoroStats } from "@/core/types";
import { Button, Field, IconButton, Input, cx, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { MediaSessionTransfer } from "@/modules/media/MediaSessionTransfer";
import { ContextChip, ContextPicker } from "./ContextPicker";
import { FocusMode } from "./FocusMode";
import { POMODORO_OPEN_EVENT, type PomodoroOpenRequest } from "./dock";
import { FOCUS_PREFERENCES_EVENT, focusPreferences, type FocusPreferences } from "./preferences";
import { clock, remaining } from "./time";

type DockView = "menu" | "focus";

/**
 * Uygulamanin genel hizli eylem yuzeyi. Bosta evrensel `+`, aktif odakta
 * kalan sure pill'i olur; sayfa degisince seans kontrolu kaybolmaz.
 */
export function QuickActionDock() {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<DockView>("menu");
  const [focusMode, setFocusMode] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [preferences, setPreferences] = useState<FocusPreferences>(focusPreferences);
  const [minutes, setMinutes] = useState(preferences.focusMinutes);
  const [topic, setTopic] = useState("");
  const [context, setContext] = useState("");
  const [finished, setFinished] = useState<PomodoroSession | null>(null);
  const online = useOnline();
  const toast = useToast();

  useEffect(() => {
    function onOpen(event: Event) {
      const detail = (event as CustomEvent<PomodoroOpenRequest>).detail ?? {};
      if (detail.topic !== undefined) setTopic(detail.topic);
      if (detail.context !== undefined) setContext(detail.context);
      setView("focus");
      setOpen(true);
    }
    function onPreferences(event: Event) {
      const next = (event as CustomEvent<FocusPreferences>).detail;
      setPreferences(next);
      setMinutes(next.focusMinutes);
    }
    window.addEventListener(POMODORO_OPEN_EVENT, onOpen);
    window.addEventListener(FOCUS_PREFERENCES_EVENT, onPreferences);
    return () => {
      window.removeEventListener(POMODORO_OPEN_EVENT, onOpen);
      window.removeEventListener(FOCUS_PREFERENCES_EVENT, onPreferences);
    };
  }, []);

  const { data: active = null } = useQuery({
    queryKey: ["pomodoro-active"],
    queryFn: () => api.get<PomodoroSession | null>("/pomodoro/active"),
    refetchInterval: 30_000,
  });
  const { data: stats } = useQuery({
    queryKey: ["pomodoro-stats", "today"],
    queryFn: () => api.get<PomodoroStats>("/pomodoro/stats?range=day"),
  });

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
        planned_min: kind === "focus" ? minutes : preferences.breakMinutes,
        kind,
        topic: kind === "focus" ? topic.trim() || undefined : undefined,
        context_entity_id: kind === "focus" ? context || undefined : undefined,
      }),
    onSuccess: () => {
      refresh();
      setOpen(false);
    },
    onError: () => toast.push("Başlatılamadı — aktif bir seans olabilir.", { tone: "danger" }),
  });
  const stop = useMutation({
    mutationFn: (interrupted: boolean) => api.post(`/pomodoro/${active?.id}/stop`, { interrupted }),
    onSuccess: (_data, interrupted) => {
      const ended = active;
      refresh();
      setOpen(false);
      if (!interrupted && ended?.context_type === "media_item" && ended.context_entity_id) setFinished(ended);
    },
  });
  const togglePause = useMutation({
    mutationFn: () => api.post(`/pomodoro/${active?.id}/${active?.paused_at ? "resume" : "pause"}`),
    onSuccess: refresh,
  });

  const left = remaining(active, now);
  const paused = Boolean(active?.paused_at);
  useEffect(() => {
    if (active && !paused && left === 0 && !stop.isPending && online) stop.mutate(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [left, active?.id, paused, online]);

  function openCaptureKind(kind?: "task" | "note") {
    setOpen(false);
    openCapture(kind ? { kind } : {});
  }

  return (
    <>
      {open && (
        <aside
          role="dialog"
          aria-label={active ? "Aktif odak seçenekleri" : view === "focus" ? "Odak başlat" : "Hızlı işlemler"}
          className="fixed bottom-20 left-4 right-4 z-popover max-h-screen overflow-y-auto rounded-overlay border border-strong bg-surface shadow-overlay sm:left-auto sm:right-5 sm:w-96"
        >
          <header className="flex items-center gap-3 border-b border-subtle px-4 py-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-control bg-accent-surface text-accent">
              {active || view === "focus" ? <Timer size={16} /> : <Plus size={16} />}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-body font-medium text-primary">
                {active ? "Aktif odak" : view === "focus" ? "Yeni odak" : "Hızlı işlemler"}
              </p>
              <p className="truncate text-meta text-muted">
                {active ? active.topic || active.context_title || "Bağımsız odak" : "Yeni bir şey başlat veya kaydet"}
              </p>
            </div>
            {!active && view === "focus" && (
              <Button size="sm" variant="ghost" onClick={() => setView("menu")}>
                geri
              </Button>
            )}
            <IconButton title="Paneli kapat" onClick={() => setOpen(false)}>
              <X size={14} />
            </IconButton>
          </header>

          {active ? (
            <div className="space-y-4 p-4">
              <div className="flex items-end justify-between gap-3">
                <div className={cx("numeral text-display tabular-nums", paused ? "text-muted" : "text-primary")}>
                  {clock(left)}
                </div>
                <ContextChip type={active.context_type} />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="primary" disabled={!online} onClick={() => setFocusMode(true)}>
                  <Maximize2 size={13} /> tam ekran
                </Button>
                <Button size="sm" disabled={!online || togglePause.isPending} onClick={() => togglePause.mutate()}>
                  {paused ? <Play size={13} /> : <Pause size={13} />}
                  {paused ? "devam" : "duraklat"}
                </Button>
                <Button size="sm" variant="ok" disabled={!online || stop.isPending} onClick={() => stop.mutate(false)}>
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
              <a
                href="#/pomodoro"
                onClick={() => setOpen(false)}
                className="block border-t border-subtle pt-3 text-meta text-accent"
              >
                Odak sayfasına git
              </a>
            </div>
          ) : view === "menu" ? (
            <div className="grid grid-cols-2 gap-2 p-3">
              <button
                type="button"
                onClick={() => openCaptureKind()}
                className="flex min-h-20 flex-col items-start justify-between rounded-card border border-subtle bg-surface p-3 text-left text-body text-primary transition hover:bg-surface-hover"
              >
                <FileText size={17} className="text-icon" />
                <span>Yeni kayıt</span>
              </button>
              <button
                type="button"
                onClick={() => setView("focus")}
                className="flex min-h-20 flex-col items-start justify-between rounded-card border border-accent-border bg-accent-surface p-3 text-left text-body font-medium text-accent transition hover:brightness-95"
              >
                <Timer size={17} />
                <span>Odak başlat</span>
              </button>
              <button
                type="button"
                onClick={() => openCaptureKind("task")}
                className="flex min-h-20 flex-col items-start justify-between rounded-card border border-subtle bg-surface p-3 text-left text-body text-primary transition hover:bg-surface-hover"
              >
                <ListChecks size={17} className="text-icon" />
                <span>Görev ekle</span>
              </button>
              <button
                type="button"
                onClick={() => openCaptureKind("note")}
                className="flex min-h-20 flex-col items-start justify-between rounded-card border border-subtle bg-surface p-3 text-left text-body text-primary transition hover:bg-surface-hover"
              >
                <StickyNote size={17} className="text-icon" />
                <span>Not al</span>
              </button>
            </div>
          ) : (
            <div className="space-y-4 p-4">
              <div>
                <p className="mb-2 text-meta text-secondary">Süre</p>
                <div className="flex flex-wrap gap-2">
                  {[25, preferences.focusMinutes, 90]
                    .filter((value, index, values) => values.indexOf(value) === index)
                    .map((preset) => (
                      <Button
                        key={preset}
                        size="sm"
                        variant={minutes === preset ? "ok" : "secondary"}
                        onClick={() => setMinutes(preset)}
                      >
                        {preset} dk
                      </Button>
                    ))}
                  <Input
                    type="number"
                    value={String(minutes)}
                    onChange={(value) =>
                      setMinutes(Math.max(1, Math.min(240, Number(value) || preferences.focusMinutes)))
                    }
                    ariaLabel="Özel odak süresi"
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
                  variant="success"
                  className="flex-1"
                  disabled={!online || start.isPending}
                  onClick={() => start.mutate("focus")}
                >
                  <Play size={14} /> {minutes} dk odak
                </Button>
                <Button disabled={!online || start.isPending} onClick={() => start.mutate("short_break")}>
                  {preferences.breakMinutes} dk mola
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
        aria-label={active ? `Odak ${clock(left)}` : "Hızlı işlem menüsünü aç"}
        onClick={() => {
          if (!active) setView("menu");
          setOpen((value) => !value);
        }}
        className={cx(
          "fixed bottom-5 right-5 z-popover flex h-11 items-center justify-center rounded-full border shadow-overlay transition",
          active
            ? "gap-2 border-accent-border bg-accent-surface px-4 text-accent hover:brightness-95"
            : "w-11 border-strong bg-surface-raised text-primary hover:bg-surface-hover",
        )}
      >
        {active ? <Timer size={16} /> : <Plus size={19} />}
        {active && <span className="numeral text-body tabular-nums">{clock(left)}</span>}
        {active && !paused && <span className="h-1.5 w-1.5 rounded-full bg-ok" aria-hidden />}
      </button>

      {focusMode && active && <FocusMode onClose={() => setFocusMode(false)} />}
      <MediaSessionTransfer session={finished} onClose={() => setFinished(null)} />
    </>
  );
}

QuickActionDock.displayName = "QuickActionDock";
