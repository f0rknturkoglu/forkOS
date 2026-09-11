/**
 * Ogrenme modulunun gorunum sozlugu.
 *
 * Konu durumu TEK kumeden gelir ve backend'deki TOPIC_STATUSES ile aynidir
 * (app/modules/learning/schemas.py). Arayuzde ayri bir durum listesi
 * tutulmaz -- ikisi ayrisirsa ice aktarma ile ekran birbirini tutmaz.
 */
import type { LearningView, TabId, TopicStatus } from "@/core/types";

export const TOPIC_STATUSES = ["not_started", "in_progress", "done"] as const;

interface StatusSpec {
  label: string;
  /** Ozet cumlesi -- secili durum ne anlama geliyor. */
  hint: string;
  tone: "neutral" | "accent" | "ok";
}

const STATUS: Record<string, StatusSpec> = {
  not_started: { label: "Başlamadı", hint: "Henüz elini sürmedin", tone: "neutral" },
  in_progress: { label: "Çalışılıyor", hint: "Şu an üzerinde çalışıyorsun", tone: "accent" },
  done: { label: "Öğrenildi", hint: "Bu konuyu tamamladın", tone: "ok" },
};

export const statusLabel = (value: string): string => STATUS[value]?.label ?? value;
const statusHint = (value: string): string => STATUS[value]?.hint ?? "";
export const statusTone = (value: string): "neutral" | "accent" | "ok" => STATUS[value]?.tone ?? "neutral";

/** Ust seviye gorunumler — `Tabs` ile cizilir, `?view=` ile senkron kalir. */
export const LEARNING_VIEWS: { id: LearningView; label: string }[] = [
  { id: "topics", label: "Konular" },
  { id: "courses", label: "Kurslar" },
  { id: "review", label: "Tekrar" },
  { id: "stats", label: "İstatistikler" },
];

/** URL'den gelen ham metni gecerli kimlige ceviren tek kaynak (bilinmeyen -> varsayilan). */
export const LEARNING_VIEW_IDS: Record<string, LearningView> = {
  topics: "topics",
  courses: "courses",
  review: "review",
  stats: "stats",
};

export const LEARNING_TAB_IDS: Record<string, TabId> = {
  genel: "genel",
  kaynaklar: "kaynaklar",
  notlar: "notlar",
  baglantilar: "baglantilar",
  tekrar: "tekrar",
};

/** Konu agacindaki durum filtresi; "all" sunucuya `status` gondermez. */
export type TopicStatusFilter = TopicStatus | "all";

/** Master-detail rayindaki hizli filtreler (istemci tarafi). */
export type TopicQuickKey = "today" | "studying" | "due";
export type TopicQuickFilter = "none" | TopicQuickKey;

/**
 * Siradaki tekrar etiketi. `due` sunucudan gelir (bugunun sonundan once);
 * tarih varsa gun farki ile birlikte yazilir.
 */
export function reviewLabel(nextReviewAt: string | null, due: boolean): string {
  if (!nextReviewAt) return "Tekrar planlanmadı";
  const day = 86_400_000;
  const diff = Math.round((new Date(nextReviewAt).getTime() - Date.now()) / day);
  if (due || diff <= 0) return "Tekrar zamanı geldi";
  if (diff === 1) return "Yarın";
  if (diff < 7) return `${diff} gün sonra`;
  if (diff < 30) return `${Math.round(diff / 7)} hafta sonra`;
  return `${Math.round(diff / 30)} ay sonra`;
}

/** Segment kontrolundeki secili/secilmemis buton siniflari. */
export function statusButtonClass(value: string, active: boolean): string {
  if (!active) return "border-transparent text-secondary hover:bg-surface-hover hover:text-primary";
  const tone = statusTone(value);
  if (tone === "ok") return "border-ok-border bg-ok-surface font-medium text-ok";
  if (tone === "accent") return "border-accent-border bg-accent-surface font-medium text-accent";
  return "border-strong bg-surface font-medium text-primary";
}
