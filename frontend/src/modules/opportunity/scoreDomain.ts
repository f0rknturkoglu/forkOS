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
const SCORE_ELIMINATED = -1;
/** "Güçlü" bandın eşiği; slider ekseni ve preset'ler buradan okur. */
export const SCORE_STRONG = 70;
/** "Orta" bandın eşiği; slider ekseni ve preset'ler buradan okur. */
export const SCORE_FAIR = 40;
/** Skorlar iki ondalıkla saklanır; preset sınırları da bu adımla kapanır. */
const SCORE_STEP = 0.01;

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

/**
 * Kalite skoru var/yok filtresi: `null` kayıtları ayrı seçebilmek için.
 *
 * Etiketler `Profil / beceri uyumu` bölümündeki "Hesaplanmadı" ile
 * karışmasın diye "kalite skoru"nu açıkça söyler.
 */
export const SCORE_STATE_PRESETS = [
  { label: "Tümü", state: undefined },
  { label: "Kalite skoru var", state: "computed" as const },
  { label: "Kalite skoru yok", state: "uncomputed" as const },
] as const;

/**
 * Kalite skorunun GÖRÜNEN değeri.
 *
 * Yukarı yuvarlama (79.6 → "80") ile "70–79" aralığı çelişirdi: filtre
 * kapsayıcı olduğu için 79.6 o aralığa girer ama ekranda 80 görünürdü.
 * Aşağı yuvarlama, görünen sayıyı aralıklarla birebir uyumlu tutar.
 */
export function displayScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return "—";
  if (score < 0) return "Elendi";
  return String(Math.floor(score));
}
