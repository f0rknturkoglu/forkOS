import { allTodayWidgets } from "./registry";

/**
 * Bugun hazir preset'leri (Faz 20).
 *
 * Preset secmek kullanici ayarini ACIKCA degistirir: siralamayi ve
 * gizlemeyi birebir yazar (gizli sihirli davranis yok). Odakli, gorevi
 * one cikarir: akis/ikincil durum widget'lari gizlidir ama ayarlardan
 * acilabilir. Genel bakis her seyi varsayilan duzende gosterir.
 */

export type TodayPreset = "focused" | "overview";

interface TodayPresetConfig {
  order: string[];
  hidden: string[];
}

/** Odakli: ikincil (defaultVisible=false) widget'lar gizli, kalanlar varsayilan order. */
export function focusedConfig(): TodayPresetConfig {
  const widgets = allTodayWidgets();
  return {
    order: widgets.map((widget) => widget.id),
    hidden: widgets.filter((widget) => widget.defaultVisible === false).map((widget) => widget.id),
  };
}

/** Genel bakis: hicbir tercih yok -- her sey varsayilan slot/order'da gorunur. */
export function overviewConfig(): TodayPresetConfig {
  return { order: [], hidden: [] };
}

export const PRESET_LABELS: Record<TodayPreset, string> = {
  focused: "Odaklı",
  overview: "Genel bakış",
};
