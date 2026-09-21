// @vitest-environment jsdom
/**
 * Ürün navigasyonu sözleşmesi: rota → alan eşleşmesi ve sidebar satırları.
 *
 * Bu testler GERÇEK registry'yi kullanır (`@/modules`): alan haritası modül
 * kimlikleriyle yazılır, dolayısıyla modül kimliği değişirse test düşer.
 */
import "@/modules";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { areaForPath, areaRows, areaShape, areasAt, moduleLanding, rowIsActive } from "./navigation";
import { allCommands, allRoutes, enabledModules, moduleForPath } from "./registry";

vi.hoisted(() => {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => store.set(key, value),
      removeItem: (key: string) => store.delete(key),
      clear: () => store.clear(),
    },
  });
});

const modules = () => enabledModules();

describe("ürün navigasyonu — rota → alan", () => {
  beforeEach(() => localStorage.clear());

  it.each([
    ["/", "home"],
    ["/todos", "plan"],
    ["/habits", "plan"],
    ["/planner", "plan"],
    ["/calendar", "plan"],
    ["/pomodoro", "plan"],
    ["/projects", "projects"],
    ["/opportunities", "career"],
    ["/learning", "learning"],
    ["/study", "learning"],
    ["/flashcard", "learning"],
    ["/bookmarks", "library"],
    ["/documents", "library"],
    ["/rss", "library"],
    ["/media", "library"],
    ["/media/library", "library"],
    ["/media/collections", "library"],
    ["/media/upcoming", "library"],
    ["/notes", "library"],
  ])("%s → %s", (path, areaId) => {
    expect(areaForPath(path, modules())?.id).toBe(areaId);
  });

  it("dinamik ve eski (compat) rotalar doğru alanı işaretler", () => {
    expect(areaForPath("/media/abc-123", modules())?.id).toBe("library");
    expect(areaForPath("/media/collections/abc-123", modules())?.id).toBe("library");
    expect(areaForPath("/media/stats", modules())?.id).toBe("library");
    // Statik eşleşme global olarak kazanır: /media/stats detay rotasına düşmez.
    expect(areaForPath("/media/trash", modules())?.id).toBe("library");
    expect(areaForPath("/statistics", modules())?.id).toBe("longtail");
    expect(areaForPath("/day", modules())?.id).toBe("longtail");
    expect(areaForPath("/review/weekly", modules())?.id).toBe("longtail");
    expect(areaForPath("/health", modules())?.id).toBe("system");
    expect(areaForPath("/sources", modules())?.id).toBe("system");
    expect(areaForPath("/settings", modules())?.id).toBe("system");
  });

  it("hiçbir alana ait olmayan yüzeyler (triyaj akışı) satır tutmaz", () => {
    expect(areaForPath("/inbox", modules())).toBeUndefined();
    expect(areaForPath("/bilinmeyen", modules())).toBeUndefined();
  });

  it("alana girmeyen modül kayıtlı kalır: rota, komut ve başlık çalışır", () => {
    // Navigasyonda satır tutmamak, modülü devre dışı bırakmak DEĞİLDİR.
    expect(allRoutes().some((route) => route.path === "/inbox")).toBe(true);
    expect(allCommands().some((command) => command.id === "inbox.open")).toBe(true);
    expect(moduleForPath("/inbox")?.id).toBe("inbox");
  });

  it("her modül rotası en fazla bir alana bağlıdır", () => {
    const owners = new Map<string, string>();
    for (const area of [...areasAt("primary"), ...areasAt("longtail"), ...areasAt("system")]) {
      for (const module of modules().filter((m) => area.moduleIds.includes(m.id))) {
        for (const route of module.routes) {
          const previous = owners.get(route.path);
          expect(previous === undefined || previous === area.id).toBe(true);
          owners.set(route.path, area.id);
        }
      }
    }
  });
});

describe("ürün navigasyonu — satırlar", () => {
  const area = (id: string) => areasAt("primary").find((candidate) => candidate.id === id)!;

  it("Plan satırları: görevler, haftalık plan, rutinler, takvim, odak", () => {
    expect(areaRows(area("plan"), modules()).map((row) => `${row.label}=${row.path}`)).toEqual([
      "Görevler=/todos",
      "Haftalık plan=/planner",
      "Rutinler=/habits",
      "Takvim=/calendar",
      "Odak=/pomodoro",
    ]);
  });

  it("Kütüphane satırları kendi domainlerini korur", () => {
    expect(areaRows(area("library"), modules()).map((row) => `${row.label}=${row.path}`)).toEqual([
      "Yer İmleri=/bookmarks",
      "Belgeler=/documents",
      "RSS=/rss",
      "Medya=/media",
      "Bilgi=/notes",
    ]);
  });

  it("Öğrenme alanı kartları ve tekrar görünümünü içerir", () => {
    const rows = areaRows(area("learning"), modules());
    expect(rows.map((row) => `${row.label}=${row.path}${row.query ? `?${row.query}` : ""}`)).toEqual([
      "Öğrenme=/learning",
      "Kartlar=/flashcard",
      "Tekrar=/learning?view=review",
    ]);
  });

  it("sistem alanı Sağlık modülünü Sistem Durumu olarak sunar", () => {
    const system = areasAt("system")[0];
    expect(areaRows(system, modules()).map((row) => row.label)).toEqual(["Sistem Durumu", "Kaynaklar", "Ayarlar"]);
  });

  it("kapalı modül satır ve rota bırakmaz", () => {
    const withoutCalendar = modules().filter((module) => module.id !== "calendar");
    expect(areaRows(area("plan"), withoutCalendar).some((row) => row.path === "/calendar")).toBe(false);
    expect(areaForPath("/calendar", withoutCalendar)).toBeUndefined();
  });

  it("kapatılmış rotalar satır olmaz, gizli rotalar da alan sahipliğini korur", () => {
    const planPaths = areaRows(area("plan"), modules()).map((row) => row.path);
    expect(planPaths).not.toContain("/study");
    expect(areaRows(area("learning"), modules()).map((row) => row.path)).not.toContain("/study");
  });

  it("alan biçimi: tek hedefli alan bağlantı, çok hedefli alan katlanır bölüm", () => {
    expect(areaShape(area("home"), modules())).toBe("link");
    expect(areaShape(area("projects"), modules())).toBe("link");
    expect(areaShape(area("career"), modules())).toBe("link");
    expect(areaShape(area("plan"), modules())).toBe("section");
    expect(areaShape(area("library"), modules())).toBe("section");
    expect(areaShape(areasAt("longtail")[0], modules())).toBe("group");
  });

  it("modül hedefi dinamik rotaya düşmez; sabitlenmiş görünüm satırı bunu kullanır", () => {
    expect(moduleLanding(modules(), "media")).toBe("/media");
    expect(moduleLanding(modules(), "opportunity")).toBe("/opportunities");
    expect(moduleLanding(modules(), "yok-boyle-modul")).toBeUndefined();
  });

  it("derin görünüm satırı sorguyla eşleşir", () => {
    const tekrar = areaRows(area("learning"), modules()).find((row) => row.label === "Tekrar")!;
    expect(rowIsActive(tekrar, "/learning", new URLSearchParams("view=review"))).toBe(true);
    expect(rowIsActive(tekrar, "/learning", new URLSearchParams())).toBe(false);
    expect(rowIsActive(tekrar, "/flashcard", new URLSearchParams("view=review"))).toBe(false);
  });
});
