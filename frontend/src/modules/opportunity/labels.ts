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

const JOB_CATEGORY_LABELS: Record<string, string> = {
  software: "Yazılım & mühendislik",
  "data-ai": "Veri & yapay zekâ",
  "product-design": "Ürün & tasarım",
  "cloud-security": "Bulut, DevOps & güvenlik",
  "business-ops": "İş, finans & operasyon",
  "sales-marketing": "Satış & pazarlama",
  other: "Diğer",
};

export const jobCategoryLabel = (category: string | null) =>
  category ? (JOB_CATEGORY_LABELS[category] ?? category) : "Kategorisiz";

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
  "discovered",
  "considering",
  "preparing",
  "applied",
  "interview",
  "offer",
  "accepted",
  "rejected",
  "withdrawn",
  "closed",
];

type StatusTone = "neutral" | "accent" | "ok" | "warn" | "danger";

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

/** Kanonik remote kovalari — backend browse facet'i (_remote_bucket) ile ayni. */
export type RemoteKind = "remote" | "hybrid" | "onsite" | "unknown";

/** Bilinen ofis sözcükleri (backend _remote_bucket ile ayni set). */
const OFFICE_WORDS = ["onsite", "office", "on-site", "ofis"];

/** Ham remote metnini kanonik kovaya cevirir: "Remote - EU" -> remote, "Hybrid" -> hybrid, "Onsite" -> onsite. Taninmayan metin -> null. */
export function remoteKind(remote: string | null): RemoteKind | null {
  if (!remote) return null;
  const t = remote.toLocaleLowerCase("tr");
  if (t.includes("remote") || t.includes("uzaktan") || t.includes("wfh") || t.includes("uzak çalışma")) {
    return "remote";
  }
  if (t.includes("hybrid") || t.includes("hibrit") || t.includes("karma")) {
    return "hybrid";
  }
  if (OFFICE_WORDS.includes(t)) {
    return "onsite";
  }
  return null;
}

export const REMOTE_LABELS: Record<RemoteKind, string> = {
  remote: "Uzaktan",
  hybrid: "Hibrit",
  onsite: "Ofis",
  unknown: "Çalışma biçimi bilinmiyor",
};
