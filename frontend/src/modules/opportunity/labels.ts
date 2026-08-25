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
  offer: "Teklif",
  accepted: "Kabul",
  rejected: "Red",
  withdrawn: "Geri çekildi",
  closed: "Kapandı",
  trashed: "Çöp",
};

/** Basvuru hattinin sirasi. Kart ve suzgecte ayni sira kullanilir. */
export const STATUSES = [
  "discovered", "considering", "preparing", "applied", "interview",
  "offer", "accepted", "rejected", "withdrawn", "closed",
];

export type StatusTone = "neutral" | "accent" | "ok" | "warn" | "danger";

export const STATUS_TONES: Record<string, StatusTone> = {
  discovered: "neutral",
  considering: "neutral",
  preparing: "accent",
  applied: "accent",
  interview: "warn",
  offer: "accent",
  accepted: "ok",
  rejected: "danger",
  withdrawn: "neutral",
  closed: "neutral",
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

/** Skor renkleri: yeşil (>=70) · sarı (40-69) · kırmızı (<0) · gri (0-39). */
export const SCORE_TONE: Record<ScoreBand, "neutral" | "warn" | "ok" | "danger"> = {
  killed: "danger",
  low: "neutral",
  fair: "warn",
  strong: "ok",
};

export type RemoteKind = "remote" | "hybrid" | "office";

/** Ham remote metnini sinifa cevirir: "Remote - EU" -> remote, "Hybrid" -> hybrid. */
export function remoteKind(remote: string | null): RemoteKind | null {
  if (!remote) return null;
  const t = remote.toLocaleLowerCase("tr");
  if (t.includes("remote") || t.includes("uzaktan") || t.includes("wfh") || t.includes("uzak çalışma")) {
    return "remote";
  }
  if (t.includes("hybrid") || t.includes("hibrit") || t.includes("karma")) {
    return "hybrid";
  }
  return "office";
}

export const REMOTE_LABELS: Record<RemoteKind, string> = {
  remote: "Uzaktan",
  hybrid: "Hibrit",
  office: "Ofis",
};