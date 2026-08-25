import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Minimize2, Pause, Play, X } from "lucide-react";
import { api } from "@/core/api";
import { Button, cx } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { PomodoroSession } from "@/core/types";
import { clock, remaining } from "./time";

/**
 * Odak modu: sayac disinda hicbir sey yok.
 *
 * Amac ekrandaki her seyi kapatmak -- listeler, rozetler, bildirim sayilari
 * odaklanirken tam da bakilmamasi gereken seyler. Kapatmak icin Esc yeter.
 *
 * Sayac yine sunucudaki `started_at`'e dayaniyor (PomodoroPage ile ayni
 * hesap), yani bu katman sadece bir gorunum; sekme kapansa da seans surer.
 */
export function FocusMode({ onClose }: { onClose: () => void }) {
  const [now, setNow] = useState(Date.now());
  const online = useOnline();

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const { data: active = null } = useQuery({
    queryKey: ["pomodoro-active"],
    queryFn: () => api.get<PomodoroSession | null>("/pomodoro/active"),
    refetchInterval: 30_000,
  });

  const stop = useMutation({
    mutationFn: (interrupted: boolean) => api.post(`/pomodoro/${active?.id}/stop`, { interrupted }),
    onSuccess: () => {
      invalidateAfter("pomodoro.write");
      onClose();
    },
  });
  const togglePause = useMutation({
    mutationFn: () => api.post(`/pomodoro/${active?.id}/${active?.paused_at ? "resume" : "pause"}`),
    onSuccess: () => invalidateAfter("pomodoro.write"),
  });

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    // Katman acikken arka plan kaymasin.
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [onClose]);

  const left = remaining(active, now);
  const paused = Boolean(active?.paused_at);

  // Sekme baslikta da kalan sureyi tasisin: baska sekmedeyken bile gorunur.
  useEffect(() => {
    if (!active) return;
    const previous = document.title;
    document.title = `${clock(left)} · ${paused ? "durakladı" : "odak"}`;
    return () => {
      document.title = previous;
    };
  }, [active, left, paused]);

  useEffect(() => {
    if (active && !paused && left === 0 && !stop.isPending && online) stop.mutate(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [left, active?.id, paused]);

  if (!active) return null;

  const total = active.planned_min * 60;
  const done = total > 0 ? 1 - left / total : 0;
  // Halka cevresi: r=140 -> 2*pi*r. Ilerleme dash offset ile ciziliyor.
  const circumference = 2 * Math.PI * 140;

  return (
    <div
      role="dialog"
      aria-label="Odak modu"
      className="fixed inset-0 z-[80] flex flex-col items-center justify-center gap-8 bg-canvas p-6"
    >
      <button
        type="button"
        onClick={onClose}
        title="Odak modundan çık (Esc)"
        aria-label="Odak modundan çık"
        className="absolute right-5 top-5 flex h-9 w-9 items-center justify-center rounded-control text-muted transition hover:bg-surface-hover hover:text-primary"
      >
        <X size={18} />
      </button>

      <p className="max-w-xl truncate text-center text-meta uppercase tracking-[0.2em] text-muted">
        {active.topic || active.context_title || "Odak"}
      </p>

      <div className="relative flex items-center justify-center">
        <svg width="320" height="320" viewBox="0 0 320 320" className="-rotate-90" aria-hidden>
          <circle cx="160" cy="160" r="140" fill="none" strokeWidth="6" className="stroke-subtle" />
          <circle
            cx="160"
            cy="160"
            r="140"
            fill="none"
            strokeWidth="6"
            strokeLinecap="round"
            className={cx(
              "transition-[stroke-dashoffset] duration-1000 ease-linear",
              left === 0 ? "stroke-ok" : paused ? "stroke-strong" : "stroke-accent",
            )}
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - done)}
          />
        </svg>
        <div className="absolute text-center">
          <div
            className={cx(
              "numeral text-display-2xl leading-none tabular-nums transition-colors",
              paused ? "text-muted" : "text-primary",
            )}
          >
            {clock(left)}
          </div>
          <p className="mt-2 text-meta text-muted">
            {paused ? "duraklatıldı" : `${active.planned_min} dakikalık blok`}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button variant="primary" disabled={!online || togglePause.isPending} onClick={() => togglePause.mutate()}>
          {paused ? (
            <>
              <Play size={14} /> devam et
            </>
          ) : (
            <>
              <Pause size={14} /> duraklat
            </>
          )}
        </Button>
        <Button disabled={!online || stop.isPending} onClick={() => stop.mutate(false)}>
          tamamla
        </Button>
        <Button variant="danger" disabled={!online || stop.isPending} onClick={() => stop.mutate(true)}>
          yarıda kes
        </Button>
        <Button variant="ghost" onClick={onClose}>
          <Minimize2 size={14} /> küçült
        </Button>
      </div>

      <p className="text-meta text-muted">Esc ile çıkarsın; sayaç arka planda devam eder.</p>
    </div>
  );
}
