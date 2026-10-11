/**
 * Modul registry.
 *
 * Yeni modul eklemek = modules/<ad>/index.ts + modules/index.ts'e bir satir.
 * Router, Today ekrani, Command Palette ve Settings BU LISTEDEN beslenir.
 * Bu dosyalarin disinda hicbir yere modul adi yazma.
 */
import { useSyncExternalStore } from "react";
import type { ComponentType } from "react";
import type { Command, ModuleSpec, TodayWidget } from "./types";
import { findRouteMatch } from "@/app/router";
import { readStored, removeStored, writeStored } from "./storage";

const registry = new Map<string, ModuleSpec>();

export function registerModule(spec: ModuleSpec): void {
  if (registry.has(spec.id)) {
    // Dev'de HMR modul dosyasini yeniden calistirir; ayni id ile ikinci kayit
    // hata degil, guncelleme demektir. Uretimde iki modul ayni id'yi
    // aliyorsa bu gercek bir cakismadir -- orada patlamali.
    if (import.meta.hot) {
      registry.set(spec.id, spec);
      return;
    }
    throw new Error(`Modul zaten kayitli: ${spec.id}`);
  }
  registry.set(spec.id, spec);
}

export const allModules = (): ModuleSpec[] => [...registry.values()];

/**
 * ACIK moduller. Kapatilan modul rota, widget ve komut getirmez; navigasyon da
 * (bkz. core/navigation) yalnizca bu listeden satir uretir.
 */
export function enabledModules(): ModuleSpec[] {
  const disabled = new Set<string>(JSON.parse(readStored("disabledModules") ?? "[]"));
  return allModules().filter((m) => !disabled.has(m.id));
}

export function hydrateSettings(settings: Record<string, unknown>): void {
  const disabled = Array.isArray(settings["modules.disabled"]) ? settings["modules.disabled"] : [];
  const order = Array.isArray(settings["today.widget_order"]) ? settings["today.widget_order"] : [];
  const widgetHidden = Array.isArray(settings["today.widget_hidden"]) ? settings["today.widget_hidden"] : [];
  writeStored("disabledModules", JSON.stringify(disabled));
  writeStored("widgetOrder", JSON.stringify(order));
  // Faz 19: widget kimlikli siralama + gizleme (modul ID sirasi legacy kalir).
  //
  // Sunucu anlik goruntusu YEREL tercihin uzerine yazmaz: kullanici bugun
  // duzeni degistirdiyse ve iki PUT'tan biri henuz ulasmadiysa (ya da dustuyse)
  // sunucudaki eski liste Home'u geri alirdi. Sunucu yalnizca bu cihazda hic
  // dokunulmamisken TOHUMLAR; tohumlayinca tercih bu cihazin tercihi olur ve
  // sonraki anlik goruntuler onu ezemez. Sunucu bos ise dokunulmaz: varsayilan
  // sozlesme (defaultVisible) gecerli kalir.
  const seeded = order.length > 0 || widgetHidden.length > 0;
  if (seeded && readStored("todayPrefsTouched") !== "1") {
    const before = prefsSignature();
    writeStored("todayWidgetOrder", JSON.stringify(order));
    writeStored("todayWidgetHidden", JSON.stringify(widgetHidden));
    writeStored("todayPrefsTouched", "1");
    if (prefsSignature() !== before) notifyPrefsChanged();
  }
  const lat = Number(settings["weather.lat"] ?? 0);
  const lon = Number(settings["weather.lon"] ?? 0);
  if (lat || lon) {
    writeStored("weather.lat", JSON.stringify(lat));
    writeStored("weather.lon", JSON.stringify(lon));
  }
}
export const allCommands = () => enabledModules().flatMap((m) => m.commands ?? []);
/** Ayarlardaki siraya gore modulleri dizer. */
function orderedModules(): ModuleSpec[] {
  const order: string[] = JSON.parse(readStored("widgetOrder") ?? "[]");
  return [...enabledModules()].sort((a, b) => {
    const ai = order.indexOf(a.id);
    const bi = order.indexOf(b.id);
    return (ai < 0 ? 999 : ai) - (bi < 0 ? 999 : bi);
  });
}

export const allTodayWidgets = () => enabledModules().flatMap((m) => m.todayWidgets ?? []);
export const allGlobalSurfaces = () => enabledModules().flatMap((m) => m.globalSurfaces ?? []);

export interface TodayWidgetView {
  id: string;
  title: string;
  widget: TodayWidget;
  moduleId: string;
}

/**
 * Widget tercihlerinin reaktif katmani.
 *
 * Tercih localStorage'da durur ama React onu render aninda imperative okuyamaz:
 * Ayarlar'dan acilan bir widget Home'a ancak yeniden mount ile yansirdi. Burada
 * tercihler tek bir "store" olarak yayinlanir:
 *   - ayni sekmede yazan her yol `forkos:today-prefs` olayini yayar,
 *   - diger sekmelerin yazimi `storage` olayiyla yakalanir.
 * `useTodayWidgetViews()` bu kaynaga abone olur; sayfa yenilemesi gerekmez.
 */
const PREFS_EVENT = "forkos:today-prefs";

/** Anlik goruntuyu ureten anahtarlar: bunlardan biri degisirse store tazelenir. */
const PREF_KEYS = ["todayPrefsTouched", "todayWidgetOrder", "todayWidgetHidden", "widgetOrder", "disabledModules"];
/** `storage` olayi TAM anahtar tasir; yalniz bu yazimlar tercih sayilir. */
const PREF_STORAGE_KEYS: Record<string, true> = Object.fromEntries(PREF_KEYS.map((key) => [`forkos.${key}`, true]));

function prefsSignature(): string {
  return PREF_KEYS.map((key) => readStored(key) ?? "").join("\u0000");
}

let viewsCache: { signature: string; visible: TodayWidgetView[]; all: TodayWidgetView[] } | null = null;

function notifyPrefsChanged(): void {
  viewsCache = null;
  window.dispatchEvent(new Event(PREFS_EVENT));
}

function onStorageWrite(event: StorageEvent): void {
  if (event.key === null || PREF_STORAGE_KEYS[event.key]) notifyPrefsChanged();
}

/** `useSyncExternalStore` sozlesmesi: abone ol, degisimde haber ver. */
function subscribeTodayWidgetPrefs(listener: () => void): () => void {
  window.addEventListener(PREFS_EVENT, listener);
  window.addEventListener("storage", onStorageWrite);
  return () => {
    window.removeEventListener(PREFS_EVENT, listener);
    window.removeEventListener("storage", onStorageWrite);
  };
}

/** Kullanicinin widget tercihleri (Faz 19): sirala + gizle. */
function readWidgetPrefs(): { order: string[]; hidden: Set<string>; touched: boolean } {
  const known = new Set(allTodayWidgets().map((w) => w.id));
  const touched = readStored("todayPrefsTouched") === "1";
  const rawOrder: unknown = JSON.parse(readStored("todayWidgetOrder") ?? "null");
  // Eski (Faz 5) deger: modul ID'leri. Widget id'lerinden hicbiri yoksa bu
  // hala modul sirasidir -- her modulun widget'larina acilir (migration).
  const legacy: string[] = JSON.parse(readStored("widgetOrder") ?? "[]");
  let order: string[] = [];
  if (Array.isArray(rawOrder) && rawOrder.some((id) => known.has(String(id)))) {
    order = rawOrder.map(String);
  } else if (legacy.length > 0) {
    const byModule = new Map(enabledModules().map((m) => [m.id, (m.todayWidgets ?? []).map((w) => w.id)]));
    order = legacy.flatMap((mid) => byModule.get(mid) ?? []);
  }
  const storedHidden = (JSON.parse(readStored("todayWidgetHidden") ?? "[]") as string[]).filter((id) => known.has(id));
  // Eski odakli varsayilan, feed gibi sonradan temel deneyime alinan
  // widget'lari hidden listesinde birakabilir. Kullanici Today duzenine henuz
  // dokunmadiysa yeni defaultVisible sozlesmesi kazanir; acik tercihler korunur.
  const hidden = new Set<string>(touched ? storedHidden : []);
  return { order: order.filter((id) => known.has(id)), hidden, touched };
}

/**
 * Home'u iki katmana ayirir:
 *   - ÇEKİRDEK: `core` alani verilmis yuzeyler. Home iskeleti; her zaman
 *     gorunur, gizlenemez ve `order` ile SABIT sirada dizilir. Kullanici
 *     sirasi/gizlemesi burada uygulanmaz (eski gizleme kayitlari cekirdegi
 *     gizleyemez).
 *   - İSTEĞE BAĞLI: kalanlar. Gizleme + kullanici sirasi burada gecerli;
 *     yerlesimleri `placement` ile belirlenir.
 * Bilinmeyen id'ler guvenle yok sayilir.
 */
function buildWidgetViews(includeHidden: boolean): TodayWidgetView[] {
  const { order, hidden, touched } = readWidgetPrefs();
  const userIndex = new Map(order.map((id, i) => [id, i]));
  const views: TodayWidgetView[] = [];
  for (const module of enabledModules()) {
    for (const widget of module.todayWidgets ?? []) {
      views.push({ id: widget.id, title: widget.title, widget, moduleId: module.id });
    }
  }
  const core = views
    .filter((view) => view.widget.core)
    .sort((a, b) => a.widget.order - b.widget.order || a.id.localeCompare(b.id));
  const optional = views
    .filter(
      (view) =>
        !view.widget.core &&
        (includeHidden || (!hidden.has(view.id) && (touched || view.widget.defaultVisible !== false))),
    )
    .sort((a, b) => {
      const ai = userIndex.has(a.id) ? userIndex.get(a.id)! : Number.MAX_SAFE_INTEGER;
      const bi = userIndex.has(b.id) ? userIndex.get(b.id)! : Number.MAX_SAFE_INTEGER;
      if (ai !== bi) return ai - bi;
      return a.widget.order - b.widget.order || a.id.localeCompare(b.id);
    });
  return [...core, ...optional];
}

/** Anlik goruntuyu imzaya gore onbellekler: referans kararli kalmali. */
function widgetViews(includeHidden: boolean): TodayWidgetView[] {
  const signature = prefsSignature();
  if (!viewsCache || viewsCache.signature !== signature) {
    viewsCache = { signature, visible: buildWidgetViews(false), all: buildWidgetViews(true) };
  }
  return includeHidden ? viewsCache.all : viewsCache.visible;
}

/**
 * Home'da gorunecek widget'lar (cekirdek iskelet + gorunur istege bagli
 * yuzeyler). Saf okuma yolu: test ve preset'ler icin.
 */
export function allTodayWidgetViews(): TodayWidgetView[] {
  return widgetViews(false);
}

/** Ayarlar ekrani icin: gizliler DAHIL tum widget'lar (siralama uygulanir). */
export function allTodayWidgetViewsIncludingHidden(): TodayWidgetView[] {
  return widgetViews(true);
}

/** Home'un canli gorunumu: tercih degisince sayfa yenilenmeden tazelenir. */
export function useTodayWidgetViews(): TodayWidgetView[] {
  return useSyncExternalStore(
    subscribeTodayWidgetPrefs,
    () => widgetViews(false),
    () => widgetViews(false),
  );
}

/** Ayarlar'in canli gorunumu: gizliler dahil (gizli olani geri acabilmek icin). */
export function useTodayWidgetViewsIncludingHidden(): TodayWidgetView[] {
  return useSyncExternalStore(
    subscribeTodayWidgetPrefs,
    () => widgetViews(true),
    () => widgetViews(true),
  );
}

/** Ayarlar ekrani: siralamayi kaydeder (backend'e yazma cagiran taraf). */
export function setTodayWidgetOrder(ids: string[]): void {
  writeStored("todayPrefsTouched", "1");
  writeStored("todayWidgetOrder", JSON.stringify(ids));
  notifyPrefsChanged();
}

export function setTodayWidgetHidden(ids: string[]): void {
  writeStored("todayPrefsTouched", "1");
  writeStored("todayWidgetHidden", JSON.stringify(ids));
  notifyPrefsChanged();
}

/** Varsayilana don: kullanici sirasi/gizleme temizlenir. */
export function resetTodayWidgetPrefs(): void {
  removeStored("todayPrefsTouched");
  removeStored("todayWidgetOrder");
  removeStored("todayWidgetHidden");
  notifyPrefsChanged();
}

export const allTodayStats = () => orderedModules().flatMap((m) => m.todayStats ?? []);
export const allRoutes = () => enabledModules().flatMap((m) => m.routes);

/** Aktif rotanin sahibi modul -- baslik ve ikon icin. */
export function moduleForPath(path: string): ModuleSpec | undefined {
  const candidates = enabledModules().flatMap((module) => module.routes.map((route) => ({ path: route.path, module })));
  return findRouteMatch(candidates, path)?.module;
}

/** Ust seritte gorunecek baslik: once rotanin kendi adi, sonra modulunki. */
export function titleForPath(path: string): string | undefined {
  const candidates = enabledModules().flatMap((module) => module.routes.map((route) => ({ ...route, module })));
  const match = findRouteMatch(candidates, path);
  return match ? (match.title ?? match.module.title) : undefined;
}
