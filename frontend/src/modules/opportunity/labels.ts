/** Fırsat türü ve durumu için Türkçe etiketler. Tek kaynak burasi. */

export const KIND_LABELS: Record<string, string> = {
  job: "İş ilanı",
  internship: "Staj",
  exam: "Sınav",
  scholarship: "Burs",
  msc: "Yüksek lisans",
  phd: "Doktora",
  grant: "Hibe",
  other: "Diğer",
};

/** Filtre seridinde bu sirayla gorunur; katalogda olmayan tur sona eklenir. */
export const KIND_ORDER = ["job", "internship", "exam", "scholarship", "msc"];

export const STATUS_LABELS: Record<string, string> = {
  discovered: "Keşfedildi",
  considering: "Değerlendiriliyor",
  preparing: "Hazırlanıyor",
  applied: "Başvuruldu",
  interview: "Görüşme",
  accepted: "Kabul",
  rejected: "Red",
  trashed: "Çöp",
};

/** Basvuru hattinin sirasi. Kart ve suzgecte ayni sira kullanilir. */
export const STATUSES = [
  "discovered", "considering", "preparing", "applied", "interview", "accepted", "rejected",
];

export type StatusTone = "neutral" | "accent" | "ok" | "warn" | "danger";

export const STATUS_TONES: Record<string, StatusTone> = {
  discovered: "neutral",
  considering: "neutral",
  preparing: "accent",
  applied: "accent",
  interview: "warn",
  accepted: "ok",
  rejected: "danger",
  trashed: "danger",
};

export const kindLabel = (kind: string) => KIND_LABELS[kind] ?? kind;
export const statusLabel = (status: string) => STATUS_LABELS[status] ?? status;

/** "jobhunter:greenhouse:adyen" -> "adyen · greenhouse" */
export function sourceLabel(source: string): string {
  const parts = source.split(":");
  if (parts[0] === "jobhunter" && parts.length >= 3) {
    return `${parts.slice(2).join(":")} · ${parts[1]}`;
  }
  return source;
}

/** Son tarihe kalan gun; gecmisse negatif. Yoksa null. */
export function daysLeft(deadline: string | null): number | null {
  if (!deadline) return null;
  const diff = new Date(deadline).getTime() - Date.now();
  return Math.ceil(diff / 86_400_000);
}

/* ── forkjob uyum puani ───────────────────────────────────────────────
   0-100 arasi. Negatif deger "kill" kelimesi yakalandi demek: kayit
   silinmez, listede geriye duser. */

export type ScoreBand = "killed" | "low" | "fair" | "strong";

export function scoreBand(score: number | null): ScoreBand | null {
  if (score === null) return null;
  if (score < 0) return "killed";
  if (score >= 70) return "strong";
  if (score >= 40) return "fair";
  return "low";
}

export const SCORE_TONE: Record<ScoreBand, "neutral" | "accent" | "ok" | "danger"> = {
  killed: "danger",
  low: "neutral",
  fair: "accent",
  strong: "ok",
};

export const SCORE_LABEL: Record<ScoreBand, string> = {
  killed: "elendi",
  low: "zayıf uyum",
  fair: "orta uyum",
  strong: "güçlü uyum",
};
