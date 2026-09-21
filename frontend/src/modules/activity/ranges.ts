/**
 * Harita zaman aralıkları — Etkinlik sayfası ve Isı Haritası sayfası AYNI
 * kaynaktan okur (aralık listesi iki yerde ayrışmasın).
 */
export const RANGES = [
  { id: "3m", label: "Son 3 ay", days: 90 },
  { id: "6m", label: "Son 6 ay", days: 180 },
  { id: "1y", label: "Son 1 yıl", days: 365 },
] as const;

export type RangeId = (typeof RANGES)[number]["id"];
