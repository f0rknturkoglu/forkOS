import { allTodayWidgets } from "./registry";

/**
 * Home hazır düzenleri (Faz 20).
 *
 * Çekirdek iskelet her düzende AYNIdır: çekirdek yüzeyler gizlenemez ve
 * sıralanamaz (bkz. `TodayWidget.core`). Preset seçmek kullanıcı tercihini
 * açıkça değiştirir ve yalnız İSTEĞE BAĞLI yüzeylere dokunur -- sihirli
 * davranış yok.
 */

export type TodayPreset = "focused" | "overview";

interface TodayPresetConfig {
  order: string[];
  hidden: string[];
}

/** İsteğe bağlı yüzeylerin kimlikleri (kayıt sırasında). */
function optionalIds(): string[] {
  return allTodayWidgets()
    .filter((widget) => !widget.core)
    .map((widget) => widget.id);
}

/** Odaklı: çekirdek iskelet kalır, isteğe bağlı yüzeylerin hepsi gizlenir. */
export function focusedConfig(): TodayPresetConfig {
  const optional = optionalIds();
  return { order: optional, hidden: optional };
}

/** Genel bakış: bütün isteğe bağlı yüzeyler görünür (varsayılan düzen). */
export function overviewConfig(): TodayPresetConfig {
  return { order: [], hidden: [] };
}

export const PRESET_LABELS: Record<TodayPreset, string> = {
  focused: "Odaklı",
  overview: "Genel bakış",
};
