import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { PomodoroSession } from "@/core/types";

/**
 * Pomodoro modulunun paylasilan sorgu anahtarlari ve hook'lari.
 *
 * Gun istatistigi bir ara `["pomodoro","stats","day"]` ve
 * `["pomodoro-stats","today"]` anahtarlariyla IKI kez cekiliyordu; dock kabuk
 * boyunca acik oldugu icin bu gercekten fazladan istek demekti.
 */
export const POMODORO_STATS_QUERY_KEY = ["pomodoro-stats", "today"] as const;

/**
 * Aktif seans icin TEK kanonik anahtar.
 *
 * Dort yuzey (dock, kabuk basligi gostergesi, Odak sayfasi, odak modu) ayni
 * seansi gosterir; ikinci bir anahtar uretmek ayni ucu iki kez sormak ve
 * birinin bayat kalmasi demektir. Tazeleme `invalidateAfter("pomodoro.write")`
 * iledir (`@/core/invalidation`), yani bu anahtar haritada tanimli olmali.
 */
const POMODORO_ACTIVE_QUERY_KEY = ["pomodoro-active"] as const;

/** Aktif seans: tum yuzeyler bu hook'u kullanir. */
export function useActivePomodoro() {
  return useQuery({
    queryKey: POMODORO_ACTIVE_QUERY_KEY,
    queryFn: () => api.get<PomodoroSession | null>("/pomodoro/active"),
    refetchInterval: 30_000,
  });
}

/**
 * Saniyelik zaman kaynagi. Tik YALNIZ calisan oturumda kurulur: bos ya da
 * duraklatilmis oturumda interval kurmak kabuktaki her yuzeyi bosa saniyede
 * bir yeniden cizerdi. Duraklatilmis oturumda `remaining` zaten duraklatma
 * anindan hesaplandigi icin bayat `now` yanlis sayac uretmez.
 */
export function usePomodoroClock(active: PomodoroSession | null | undefined) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    setNow(Date.now());
    if (!active || active.paused_at) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [active?.id, active?.paused_at]);
  return now;
}
