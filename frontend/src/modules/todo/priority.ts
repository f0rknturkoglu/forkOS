/**
 * Oncelik gosterimi tek yerde.
 *
 * Arayuzde "p2" gibi ic kodlar YAZILMAZ; kullanici duz Turkce gorur.
 * Renk semantik tonlardan gelir (index.css), marka rengi degil.
 */
import { daysBetween, keyToUtc, localDateKey, todayKey } from "@/lib/date";
export const PRIORITIES = [
  { value: 0, label: "yok", dot: "bg-icon", text: "text-muted", tone: "neutral" },
  { value: 1, label: "düşük", dot: "bg-ok", text: "text-ok", tone: "ok" },
  { value: 2, label: "orta", dot: "bg-warn", text: "text-warn", tone: "warn" },
  { value: 3, label: "yüksek", dot: "bg-danger", text: "text-danger", tone: "danger" },
] as const;

export const priorityOf = (value: number) => PRIORITIES[value] ?? PRIORITIES[0];

export const RECURRENCES = [
  { value: "", label: "tek seferlik" },
  { value: "daily", label: "her gün" },
  { value: "weekdays", label: "hafta içi" },
  { value: "weekly", label: "haftalık" },
  { value: "monthly", label: "aylık" },
] as const;

export const recurLabel = (value: string | null): string | null =>
  RECURRENCES.find((item) => item.value === (value ?? ""))?.label ?? null;

/** Bugun / yarin / gecikmis gibi insan diline yakin tarih etiketi. */
export function dueLabel(iso: string | null): { text: string; tone: "muted" | "accent" | "danger" } | null {
  if (!iso) return null;
  const due = new Date(iso);
  // Gun karsilastirmasi app tz'de (Faz 14): tarayicinin yerel saati degil.
  const diff = daysBetween(todayKey(), localDateKey(due));

  const time =
    due.getHours() || due.getMinutes() ? due.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }) : "";
  const withTime = (label: string) => (time ? `${label} ${time}` : label);

  if (diff < 0) return { text: withTime(diff === -1 ? "dün" : `${-diff} gün gecikti`), tone: "danger" };
  if (diff === 0) return { text: withTime("bugün"), tone: "accent" };
  if (diff === 1) return { text: withTime("yarın"), tone: "muted" };
  if (diff < 7) return { text: withTime(due.toLocaleDateString("tr-TR", { weekday: "long" })), tone: "muted" };
  return {
    text: withTime(
      keyToUtc(localDateKey(due)).toLocaleDateString("tr-TR", {
        timeZone: "UTC",
        day: "numeric",
        month: "short",
      }),
    ),
    tone: "muted",
  };
}

/**
 * Plan etiketi (plan_slot) -- due_at'ten AYRI kavram: "bugun yapmayi
 * planliyorum" diyen slotun gorunur hali. Gecmis gune planlanmis ama
 * yapilmamis gorev uyari tonu alir; backend gecmis slot donmese de
 * bu emniyet kolu geri gelirse bozulmadan kalir.
 */
export function planLabel(
  plannedDay: string | null,
  startMin: number | null,
): { text: string; tone: "muted" | "accent" | "warn" } | null {
  if (!plannedDay) return null;
  // Plan gunu karsilastirmasi app tz'de (Faz 14) -- plan_day zaten app gunudur.
  const diff = daysBetween(todayKey(), plannedDay);

  const time =
    startMin != null
      ? `${String(Math.floor(startMin / 60)).padStart(2, "0")}:${String(startMin % 60).padStart(2, "0")}`
      : "";
  const withTime = (label: string) => (time ? `${label} ${time}` : label);

  if (diff < 0) return { text: withTime("gecikmiş plan"), tone: "warn" };
  if (diff === 0) return { text: withTime("bugün planlı"), tone: "accent" };
  if (diff === 1) return { text: withTime("yarın planlı"), tone: "muted" };
  return {
    text: withTime(
      keyToUtc(plannedDay).toLocaleDateString("tr-TR", {
        timeZone: "UTC",
        day: "numeric",
        month: "short",
      }) + " planlı",
    ),
    tone: "muted",
  };
}
