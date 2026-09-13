import { type ScoreBand, scoreBand } from "./scoreDomain";
/** Fırsat türü ve durumu için Türkçe etiketler. Tek kaynak burasi. */

export const KIND_LABELS: Record<string, string> = {
  job: "İş ilanı",
  internship: "Staj",
  announcement: "Duyuru",
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

const ANNOUNCEMENT_CATEGORY_LABELS: Record<string, string> = {
  "ylsy-application": "YLSY başvuru",
  "ylsy-exam": "YLSY sınav",
  "ylsy-extension": "Süre uzatımı",
  "ylsy-guide": "YLSY kılavuz",
  "ylsy-language": "Dil eğitimi",
  "ylsy-preference": "Kurum tercihi",
  "ylsy-public-slot": "Kamu kontenjanı",
  "ylsy-result": "YLSY sonuç",
  "ylsy-university-slot": "Üniversite kontenjanı",
};

export const announcementCategoryLabel = (category: string | null) =>
  category ? (ANNOUNCEMENT_CATEGORY_LABELS[category] ?? "YLSY duyuru") : "Duyuru";

/**
 * Keşif ve duyuru yaşam döngüsü etiketleri (`opportunity.status`).
 *
 * Basvuru hatti ARTIK BURADA DEGIL: `APPLICATION_STATUS_LABELS`'ta. İki kume
 * karıştırılmaz; backend `/opportunities/lifecycle` izinli geçişleri verir.
 */
export const STATUS_LABELS: Record<string, string> = {
  // İş ilanı keşif döngüsü
  discovered: "Keşfedildi",
  shortlisted: "Kısa listede",
  dismissed: "Elendi",
  archived: "Arşivde",
  closed: "Kapandı",
  // Duyuru döngüsü
  new: "Yeni",
  reviewed: "İncelendi",
  watching: "Takipte",
  action_required: "Aksiyon gerekli",
  applied: "Başvuruldu",
  completed: "Tamamlandı",
  expired: "Süresi geçti",
  // Eski (0050 öncesi) kayıtlar için okunabilir karşılıklar
  considering: "Kısa listede",
  preparing: "Kısa listede",
  interview: "Kısa listede",
  offer: "Kısa listede",
  accepted: "Arşivde",
  rejected: "Arşivde",
  withdrawn: "Arşivde",
  trashed: "Elendi",
};

/** İş ilanı keşif sırası (kanban/liste sırası). */
export const JOB_DISCOVERY_STATUSES = ["discovered", "shortlisted", "dismissed", "archived", "closed"] as const;

/** Duyuru yaşam döngüsü sırası. */
export const ANNOUNCEMENT_STATUSES = [
  "new",
  "reviewed",
  "watching",
  "action_required",
  "applied",
  "completed",
  "expired",
  "archived",
] as const;

/** Backend uçmuyorsa kullanılan yedek keşif akışı (kanban/özet için). */
export const STATUSES = [...JOB_DISCOVERY_STATUSES];

/** Başvuru hattı (`application.status`) — CRM ekranının kümesi. */
const APPLICATION_STATUS_LABELS: Record<string, string> = {
  preparing: "Hazırlanıyor",
  applied: "Başvuruldu",
  interview: "Görüşme",
  offer: "Teklif",
  accepted: "Kabul",
  rejected: "Red",
  withdrawn: "Geri çekildi",
  closed: "Kapandı",
  // Eski kayıtlar
  considering: "Hazırlanıyor",
  discovered: "Hazırlanıyor",
};

export const APPLICATION_STATUSES = [
  "preparing",
  "applied",
  "interview",
  "offer",
  "accepted",
  "rejected",
  "withdrawn",
  "closed",
] as const;

export const applicationStatusLabel = (status: string) => APPLICATION_STATUS_LABELS[status] ?? status;

type StatusTone = "neutral" | "accent" | "ok" | "warn" | "danger";

export const STATUS_TONES: Record<string, StatusTone> = {
  discovered: "neutral",
  shortlisted: "accent",
  dismissed: "neutral",
  archived: "neutral",
  closed: "neutral",
  new: "accent",
  reviewed: "neutral",
  watching: "warn",
  action_required: "warn",
  applied: "accent",
  completed: "ok",
  expired: "danger",
  trashed: "danger",
  considering: "accent",
  preparing: "accent",
  interview: "warn",
  offer: "accent",
  accepted: "ok",
  rejected: "danger",
  withdrawn: "neutral",
};

export const APPLICATION_STATUS_TONES: Record<string, StatusTone> = {
  preparing: "neutral",
  applied: "accent",
  interview: "warn",
  offer: "accent",
  accepted: "ok",
  rejected: "danger",
  withdrawn: "neutral",
  closed: "neutral",
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

/** Skor renkleri: yeşil (>=70) · sarı (40-69) · kırmızı (elendi) · gri (0-39). */
export const SCORE_TONE: Record<ScoreBand, "neutral" | "warn" | "ok" | "danger"> = {
  unknown: "neutral",
  eliminated: "danger",
  low: "neutral",
  fair: "warn",
  strong: "ok",
};

/** Bandın kullanıcı dilindeki adı; `unknown` "hesaplanmadı" demektir. */
export const SCORE_BAND_LABELS: Record<ScoreBand, string> = {
  unknown: "Skor hesaplanmadı",
  eliminated: "Elendi",
  low: "Düşük uyum",
  fair: "Orta uyum",
  strong: "Güçlü uyum",
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

export const ARCHETYPE_LABELS: Record<string, string> = {
  fde: "FDE",
  sa: "Solutions Architect",
  pm: "Product Manager",
  llmops: "LLMOps",
  agentic: "Agentic Systems",
  transformation: "Transformation",
};

export const archetypeLabel = (archetype: string | null | undefined): string =>
  archetype ? (ARCHETYPE_LABELS[archetype] ?? archetype) : "";

export const RECOMMENDATION_LABELS: Record<string, string> = {
  pursue: "Başvurmaya değer",
  consider: "Değerlendirilebilir",
  skip: "Pas geç",
};

export const recommendationLabel = (rec: string | null | undefined): string =>
  rec ? (RECOMMENDATION_LABELS[rec] ?? rec) : "";

export function recommendationTone(rec: string | null | undefined): "ok" | "warn" | "danger" | "neutral" {
  if (rec === "pursue") return "ok";
  if (rec === "consider") return "warn";
  if (rec === "skip") return "danger";
  return "neutral";
}

// Skor bandı tek kaynaktan gelir (scoreDomain); burada yeniden dışa aktarılır.
export { scoreBand };

/* ── Kaynak ve değerlendirme durumu ──────────────────────────────────── */

/** Kaynak gözlemi durumları (backend SOURCE_STATUS_PRIORITY ile aynı küme). */
export const SOURCE_STATUS_LABELS: Record<string, string> = {
  active: "Yayında",
  missing: "Kaynakta bulunamıyor",
  likely_closed: "Muhtemelen kapandı",
  closed: "Kaynakta kapandı",
};

/** Değerlendirme bayatlama nedenleri (backend EVALUATION_STALE_REASONS). */
export const STALE_REASON_HINTS: Record<string, string> = {
  version: "Değerlendirme kuralları güncellendi; yeniden hesapla.",
  listing: "İlan metni değişti; değerlendirme eski içeriğe göre.",
  profile: "Profil veya beceri ağırlıkları değişti; değerlendirme eski ayara göre.",
  missing: "Değerlendirme parmak izi yazılmamış; yeniden hesapla.",
};
