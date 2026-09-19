/**
 * Pomodoro modulunun paylasilan sorgu anahtarlari.
 *
 * Gun istatistigi bir ara `["pomodoro","stats","day"]` ve
 * `["pomodoro-stats","today"]` anahtarlariyla IKI kez cekiliyordu; dock kabuk
 * boyunca acik oldugu icin bu gercekten fazladan istek demekti.
 */
export const POMODORO_STATS_QUERY_KEY = ["pomodoro-stats", "today"] as const;
