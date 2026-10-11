// @vitest-environment jsdom
/**
 * Kayıtlı rota matrisi (Polish 2 §81/§82).
 *
 * Karşılığı olmayan bir hedef (ör. `/today?triage=inbox`) kullanıcıyı
 * "Böyle bir sayfa yok" ekranına düşürür. Ürün yüzeyleri ve bilinçli olarak
 * korunan gizli uyumluluk rotaları tek yerde doğrulanır: hepsi bir modül
 * rotasına çözülmeli ve bir modül tarafından sahiplenilmeli.
 */
import "@/modules"; // registerModule cagrilari
import { describe, expect, it, vi } from "vitest";
import { findRouteMatch } from "@/app/router";
import { allRoutes, moduleForPath } from "@/core/registry";

// jsdom 30 + Node 26 localStorage getter sorunu (CaptureDialog.test ile ayni):
// registry modul tercihlerini okurken localStorage'a dokunur.
vi.hoisted(() => {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => {
        store.set(key, value);
      },
      removeItem: (key: string) => {
        store.delete(key);
      },
      clear: () => store.clear(),
    },
  });
});

/** Sidebar/komut hedefleri: kullanıcı etkileşimiyle açılan rotalar. */
const PRODUCT_ROUTES = [
  "/",
  "/todos",
  "/planner",
  "/projects",
  "/opportunities",
  "/learning",
  "/bookmarks",
  "/feed",
  "/activity",
  "/review/daily",
  "/settings",
  "/inbox",
];

/** Gizli uyumluluk: eski kayıtlar ve derin bağlantılar kırılmasın diye durur. */
const COMPAT_ROUTES = ["/health", "/sources", "/rss", "/activity/heatmap", "/statistics", "/day"];

const ALL = [...PRODUCT_ROUTES, ...COMPAT_ROUTES];

describe("rota matrisi", () => {
  it.each(ALL)("%s kayıtlı bir rotaya çözülür", (path) => {
    expect(findRouteMatch(allRoutes(), path)).toBeDefined();
    expect(moduleForPath(path)).toBeDefined();
  });

  it("emekli ürün yüzeyleri gizli uyumluluk olarak kalır (rota açık, navigasyonda satır yok)", () => {
    for (const path of ["/activity/heatmap"]) {
      expect(findRouteMatch(allRoutes(), path)?.navigation).toBe("hidden");
    }
  });
});
