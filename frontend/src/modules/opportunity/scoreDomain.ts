/**
 * Skor evreni: eşikler ve hazır aralıklar TEK yerde.
 *
 * forkOS bir ilanda ÜÇ ayrı skor taşır ve bunlar karıştırılmaz:
 *
 *  - **Kalite skoru** (`score`): kaynak/kural tabanlı ilan kalitesi, `-1..100`.
 *    `-1` = elendi, `null` = hiç hesaplanmadı. `0` ile `null` AYNI ŞEY DEĞİL.
 *  - **Profil uyumu** (`skill_match_ratio`): `0..1` oranı; `null` = hesaplanmadı.
 *  - **Tavsiye skoru** (`evaluation.score`): CV ile iki aşamalı değerlendirme,
 *    `0..100`.
 *
 * Arayüzde TEK ana skor (kalite) gösterilir; diğer ikisi açıklanabilir detayda
 * yaşar. Aralık presetleri, etiketler ve varyant sayımı buradan türetilir.
 *
 * Backend karşılığı: `backend/app/modules/opportunity/scoring.py`.
 */

export const SCORE_FLOOR = -1;
export const SCORE_CAP = 100;
export const SCORE_ELIMINATED = -1;
export const SCORE_STRONG = 70;
export const SCORE_FAIR = 40;
/** Skorlar iki ondalıkla saklanır; preset sınırları da bu adımla kapanır. */
export const SCORE_STEP = 0.01;

export type ScoreBand = "unknown" | "eliminated" | "low" | "fair" | "strong";

/**
 * Skoru bandına çevirir. `unknown` = skor yok (hesaplanmadı); bu, `low`
 * (0–39) ile karıştırılmamalıdır.
 */
export function scoreBand(score: number | null | undefined): ScoreBand {
  if (score === null || score === undefined) return "unknown";
  if (score < 0) return "eliminated";
  if (score >= SCORE_STRONG) return "strong";
  if (score >= SCORE_FAIR) return "fair";
  return "low";
}

/** Preset aralıkları: `{-1} ∪ [0,100]` evrenini boşluksuz ve çakışmasız kaplar. */
export const SCORE_RANGES = [
  { label: "Tümü", min: undefined, max: undefined },
  { label: "80–100", min: 80, max: SCORE_CAP },
  { label: "70–79", min: SCORE_STRONG, max: 80 - SCORE_STEP },
  { label: "40–69", min: SCORE_FAIR, max: SCORE_STRONG - SCORE_STEP },
  { label: "0–39", min: 0, max: SCORE_FAIR - SCORE_STEP },
  { label: "Elendi", min: SCORE_ELIMINATED, max: SCORE_ELIMINATED },
] as const;

/** Skor yok filtresi: `null` kayıtları ayrı seçebilmek için. */
export const SCORE_STATE_PRESETS = [
  { label: "Tümü", state: undefined },
  { label: "Hesaplanmış", state: "computed" as const },
  { label: "Hesaplanmadı", state: "uncomputed" as const },
] as const;
