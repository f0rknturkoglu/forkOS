import type { PomodoroSession } from "@/core/types";

/** Varsayılan blok: 50 dk odak / 10 dk mola. */
export const FOCUS_MIN = 50;
export const BREAK_MIN = 10;

/** Duraklatılmış seansta zaman, duraklatma anında sabit kalır. */
export function remaining(session: PomodoroSession | null | undefined, now: number) {
  if (!session) return 0;
  const until = session.paused_at ? new Date(session.paused_at).getTime() : now;
  const elapsed = Math.floor((until - new Date(session.started_at).getTime()) / 1000) - session.paused_s;
  return Math.max(0, session.planned_min * 60 - Math.max(0, elapsed));
}

export function clock(seconds: number) {
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}
