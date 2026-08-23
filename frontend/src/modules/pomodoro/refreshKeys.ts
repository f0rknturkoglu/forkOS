export const POMODORO_REFRESH_KEYS = [
  "pomodoro-active", "pomodoro-stats", "pomodoro-sessions", "activity", "review-preview",
] as const;

export const POMODORO_TIMELINE_REFRESH_KEYS = [
  ...POMODORO_REFRESH_KEYS, "project-timeline",
] as const;
