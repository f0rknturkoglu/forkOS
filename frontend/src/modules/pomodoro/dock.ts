export const POMODORO_OPEN_EVENT = "forkos:pomodoro-open";

export interface PomodoroOpenRequest {
  context?: string;
  topic?: string;
}

/** Sayfa degistirmeden global Pomodoro panelini acar ve baglami doldurur. */
export function openPomodoro(detail: PomodoroOpenRequest = {}): void {
  window.dispatchEvent(new CustomEvent<PomodoroOpenRequest>(POMODORO_OPEN_EVENT, { detail }));
}
