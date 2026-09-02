/**
 * Ogrenme modulunun gorunum sozlugu.
 *
 * Konu durumu TEK kumeden gelir ve backend'deki TOPIC_STATUSES ile aynidir
 * (app/modules/learning/schemas.py). Arayuzde ayri bir durum listesi
 * tutulmaz -- ikisi ayrisirsa ice aktarma ile ekran birbirini tutmaz.
 */

export const TOPIC_STATUSES = ["not_started", "in_progress", "done"] as const;

interface StatusSpec {
  label: string;
  /** Ozet cumlesi -- secili durum ne anlama geliyor. */
  hint: string;
  tone: "neutral" | "accent" | "ok";
}

const STATUS: Record<string, StatusSpec> = {
  not_started: { label: "Başlamadı", hint: "Henüz elini sürmedin", tone: "neutral" },
  in_progress: { label: "Çalışıyorum", hint: "Şu an üzerinde çalışıyorsun", tone: "accent" },
  done: { label: "Bitti", hint: "Bu konuyu tamamladın", tone: "ok" },
};

export const statusLabel = (value: string): string => STATUS[value]?.label ?? value;
export const statusHint = (value: string): string => STATUS[value]?.hint ?? "";
export const statusTone = (value: string): "neutral" | "accent" | "ok" => STATUS[value]?.tone ?? "neutral";

/** Segment kontrolundeki secili/secilmemis buton siniflari. */
export function statusButtonClass(value: string, active: boolean): string {
  if (!active) return "border-transparent text-secondary hover:bg-surface-hover hover:text-primary";
  const tone = statusTone(value);
  if (tone === "ok") return "border-ok-border bg-ok-surface font-medium text-ok";
  if (tone === "accent") return "border-accent-border bg-accent-surface font-medium text-accent";
  return "border-strong bg-surface font-medium text-primary";
}
