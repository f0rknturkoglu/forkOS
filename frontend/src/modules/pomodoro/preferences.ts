export const FOCUS_MIN = 50;
export const BREAK_MIN = 10;

const FOCUS_MINUTES_KEY = "forkos.focus.minutes";
const BREAK_MINUTES_KEY = "forkos.focus.breakMinutes";
const AMOLED_KEY = "forkos.focus.amoled";
export const FOCUS_PREFERENCES_EVENT = "forkos:focus-preferences";

export interface FocusPreferences {
  focusMinutes: number;
  breakMinutes: number;
  amoled: boolean;
}

function bounded(raw: string | null, fallback: number, min: number, max: number): number {
  if (raw === null || raw.trim() === "") return fallback;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? Math.max(min, Math.min(max, parsed)) : fallback;
}

export function focusPreferences(): FocusPreferences {
  if (typeof localStorage === "undefined") {
    return { focusMinutes: FOCUS_MIN, breakMinutes: BREAK_MIN, amoled: true };
  }
  return {
    focusMinutes: bounded(localStorage.getItem(FOCUS_MINUTES_KEY), FOCUS_MIN, 1, 240),
    breakMinutes: bounded(localStorage.getItem(BREAK_MINUTES_KEY), BREAK_MIN, 1, 60),
    amoled: localStorage.getItem(AMOLED_KEY) !== "0",
  };
}

export function setFocusPreferences(value: FocusPreferences): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(FOCUS_MINUTES_KEY, String(value.focusMinutes));
  localStorage.setItem(BREAK_MINUTES_KEY, String(value.breakMinutes));
  localStorage.setItem(AMOLED_KEY, value.amoled ? "1" : "0");
  window.dispatchEvent(new CustomEvent<FocusPreferences>(FOCUS_PREFERENCES_EVENT, { detail: value }));
}
