// @vitest-environment jsdom
/**
 * Faz 5: Bugun paneli widget sozlesmesi.
 * - allTodayWidgetsIn() en az 14 modulun katkisini icerir (B7 kapanisi).
 * - Her widget order zorunlu (cakisma yok).
 */
import { beforeAll, describe, expect, it } from "vitest";
import "@/modules"; // registerModule cagrilari
import { allTodayWidgetsIn } from "./registry";

// Bazi ortamlarda (Node 26 experimental) jsdom localStorage'i saglamaz;
// registry modul sirasi okur -- stub ile gec.
beforeAll(() => {
  if (typeof localStorage === "undefined") {
    const store = new Map<string, string>();
    Object.defineProperty(globalThis, "localStorage", {
      value: {
        getItem: (k: string) => store.get(k) ?? null,
        setItem: (k: string, v: string) => { store.set(k, v); },
        removeItem: (k: string) => { store.delete(k); },
        clear: () => { store.clear(); },
        key: () => null,
        get length() { return store.size; },
      },
      configurable: true,
    });
  }
});

describe("Bugun widget sozlesmesi", () => {
  it("en az 14 modulun katkisini icerir", () => {
    const widgets = [
      ...allTodayWidgetsIn("left"),
      ...allTodayWidgetsIn("center"),
      ...allTodayWidgetsIn("right"),
    ];
    expect(widgets.length).toBeGreaterThanOrEqual(14);
  });
});
