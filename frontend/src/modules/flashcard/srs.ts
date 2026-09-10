/**
 * SM-2 zamanlama tahmini -- backend `flashcard/service.sm2_next` ile AYNI kurallar.
 *
 * Neden arayuzde: kullanici "Iyi" derse kartin ne zaman geri gelecegini
 * DERECEYI VERMEDEN once gormeli (Anki'nin en cok sevilen yani bu). Ayni
 * matematigi iki yerde tutmak riskli; `srs.test.ts` iki tarafin sabitlerini
 * birlikte dogrular.
 */

/** Derece -> (puan, etiket). 0=Yine, 1=Zor, 2=Iyi, 3=Kolay. */
const GRADES = [
  { grade: 0, label: "Yine", tone: "danger" },
  { grade: 1, label: "Zor", tone: "warn" },
  { grade: 2, label: "İyi", tone: "primary" },
  { grade: 3, label: "Kolay", tone: "ok" },
] as const;

export type GradeTone = (typeof GRADES)[number]["tone"];

/** Backend sabitleri (app/modules/flashcard/service.py). */
const NEW_INTERVAL_DAYS: Record<number, number> = { 0: 0, 1: 1, 2: 1, 3: 4 };
const EASE_DELTA: Record<number, number> = { 0: -0.2, 1: -0.15, 2: 0, 3: 0.15 };
const MIN_EASE = 1.3;

/** Yeni kartin "Yine" cezasindan sonraki geri gelme suresi (dakika). */
const AGAIN_MINUTES = 10;

interface SrsCardState {
  interval_days: number;
  ease: number;
  /** true = hic tekrar edilmemis kart (due_at null). */
  isNew: boolean;
}

function roundInterval(value: number): number {
  return Math.max(1, Math.round(value));
}

/** Bir derecenin uretecegi aralik: (gun, dakika_bazli_mi). */
export function predictInterval(card: SrsCardState, grade: number): { days: number; minutes: number | null } {
  const ease = Math.max(MIN_EASE, Math.round((card.ease + EASE_DELTA[grade]) * 100) / 100);
  if (card.isNew) {
    const days = NEW_INTERVAL_DAYS[grade];
    return grade === 0 ? { days: 0, minutes: AGAIN_MINUTES } : { days, minutes: null };
  }
  if (grade === 0) return { days: roundInterval(card.interval_days * 0.5), minutes: null };
  if (grade === 1) return { days: roundInterval(card.interval_days * 1.2), minutes: null };
  if (grade === 2) return { days: roundInterval(card.interval_days * ease), minutes: null };
  return { days: roundInterval(card.interval_days * ease * 1.3), minutes: null };
}

/** "10 dk" · "1 gün" · "3 gün" · "2 ay" -- buton ustunde gorunen kisa metin. */
export function formatInterval(days: number, minutes: number | null): string {
  if (minutes !== null) return `${minutes} dk`;
  if (days < 30) return `${days} gün`;
  const months = Math.round(days / 30);
  if (months < 12) return `${months} ay`;
  return `${(days / 365).toFixed(1)} yıl`;
}

/** Dort derece icin onizleme: [{grade, label, tone, hint}] -- butonlar bunu cizer. */
export function predictNextIntervals(card: SrsCardState) {
  return GRADES.map((entry) => {
    const { days, minutes } = predictInterval(card, entry.grade);
    return { ...entry, hint: formatInterval(days, minutes), days, minutes };
  });
}
