import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { entityRoute } from "@/core/entityRegistry";
import { Section } from "@/core/ui";
import { appTimeParts, todayKey } from "@/lib/date";
import type { TodayAgenda } from "@/core/types";

/**
 * Şimdi / Sırada (P2 §21).
 *
 * Home'un en yüksek görsel önceliği şu sorudur: "şu an ne yapıyorum, sırada ne
 * var?". Bu yüzey günün TAKVİMLİ satırlarından yalnız 1 güncel + 3 sıradaki
 * kaydı gösterir; tüm görev veritabanı Home'a dökülmez (tam liste Plan'da).
 *
 * Veri `GET /today/agenda` ile AYNIdır: TodayAgendaWidget ile aynı sorgu
 * anahtarı kullanılır, böylece Home'a ikinci bir istek eklenmez.
 */

const UPCOMING_LIMIT = 3;
/** Süre verilmezse makul varsayılan blok (agenda ile aynı kabul). */
const DEFAULT_DURATION_MIN = 30;

interface TimedItem {
  id: string;
  title: string;
  start: number;
  end: number;
  startMin: number;
  href: string | null;
}

/** Dakikada bir tazelenen "şimdi": yüzey kendiliğinden ilerler. */
function useNowMinute(): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(timer);
  }, []);
  return now;
}

function clockLabel(minutes: number): string {
  const hour = Math.floor(minutes / 60);
  const minute = minutes % 60;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function timedItems(agenda: TodayAgenda | undefined): TimedItem[] {
  return (agenda?.timed ?? [])
    .filter((row) => !row.completed && !row.context_only && row.starts_at)
    .map((row) => {
      const startsAt = new Date(row.starts_at as string);
      const duration = row.duration_min ?? DEFAULT_DURATION_MIN;
      const start = startsAt.getTime();
      // Saat etiketi uygulama saat diliminden okunur (liste ile ayni kabul).
      const parts = appTimeParts(startsAt);
      return {
        id: row.id,
        title: row.title,
        start,
        end: start + duration * 60_000,
        startMin: parts.hour * 60 + parts.minute,
        href: row.entity_id && row.entity_type ? entityRoute(row.entity_type, row.entity_id) : null,
      };
    })
    .sort((a, b) => a.start - b.start);
}

function Row({ label, item, tone }: { label: string; item: TimedItem; tone: "now" | "next" }) {
  const body = (
    <>
      <span className="w-11 shrink-0 tabular-nums text-meta text-muted">{clockLabel(item.startMin)}</span>
      <span className="min-w-0 flex-1 truncate text-body text-primary">{item.title}</span>
      <span className={`shrink-0 text-micro uppercase tracking-[0.12em] ${tone === "now" ? "text-accent" : "text-muted"}`}>
        {label}
      </span>
    </>
  );
  return item.href ? (
    <a href={item.href} className="flex items-center gap-2.5 py-1.5 hover:text-accent">
      {body}
    </a>
  ) : (
    <div className="flex items-center gap-2.5 py-1.5">{body}</div>
  );
}

export function NowNextWidget() {
  const now = useNowMinute();
  const day = todayKey();
  const { data: agenda } = useQuery({
    queryKey: ["today-agenda", day],
    queryFn: () => api.get<TodayAgenda>(`/today/agenda?day=${day}`),
  });

  const items = timedItems(agenda);
  if (items.length === 0) return null;

  const stamp = now.getTime();
  const current = [...items].reverse().find((item) => item.start <= stamp && stamp < item.end);
  const upcoming = items.filter((item) => item.start > stamp).slice(0, UPCOMING_LIMIT);
  if (!current && upcoming.length === 0) return null;

  return (
    <Section title="Şimdi ve sırada">
      {current && <Row label="şimdi" item={current} tone="now" />}
      {upcoming.map((item) => (
        <Row key={item.id} label="sırada" item={item} tone="next" />
      ))}
    </Section>
  );
}
