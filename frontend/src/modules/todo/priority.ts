/**
 * Oncelik gosterimi tek yerde.
 *
 * Arayuzde "p2" gibi ic kodlar YAZILMAZ; kullanici duz Turkce gorur.
 * Renk semantik tonlardan gelir (index.css), marka rengi degil.
 */
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
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const day = new Date(due);
  day.setHours(0, 0, 0, 0);
  const diff = Math.round((day.getTime() - today.getTime()) / 86_400_000);

  const time =
    due.getHours() || due.getMinutes() ? due.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }) : "";
  const withTime = (label: string) => (time ? `${label} ${time}` : label);

  if (diff < 0) return { text: withTime(diff === -1 ? "dün" : `${-diff} gün gecikti`), tone: "danger" };
  if (diff === 0) return { text: withTime("bugün"), tone: "accent" };
  if (diff === 1) return { text: withTime("yarın"), tone: "muted" };
  if (diff < 7) return { text: withTime(due.toLocaleDateString("tr-TR", { weekday: "long" })), tone: "muted" };
  return {
    text: withTime(due.toLocaleDateString("tr-TR", { day: "numeric", month: "short" })),
    tone: "muted",
  };
}
