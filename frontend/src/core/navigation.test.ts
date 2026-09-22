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
    ["/rss", "library"],
    ["/media", "library"],
    ["/media/library", "library"],
    ["/media/collections", "library"],
    ["/media/upcoming", "library"],
    ["/notes", "library"],
    ["/feed", "library"],
    ["/finance", "finance"],
    ["/activity", "activity"],
    ["/activity/heatmap", "activity"],
    ["/review/weekly", "review"],
    ["/review/daily", "review"],
  ])("%s → %s", (path, areaId) => {
    expect(areaForPath(path, modules())?.id).toBe(areaId);
  });

  it("dinamik ve eski (compat) rotalar doğru alanı işaretler", () => {
    expect(areaForPath("/media/abc-123", modules())?.id).toBe("library");
    expect(areaForPath("/media/collections/abc-123", modules())?.id).toBe("library");
    expect(areaForPath("/media/stats", modules())?.id).toBe("library");
    // Statik eşleşme global olarak kazanır: /media/stats detay rotasına düşmez.
    expect(areaForPath("/media/trash", modules())?.id).toBe("library");
    expect(areaForPath("/statistics", modules())?.id).toBe("activity");
    expect(areaForPath("/day", modules())?.id).toBe("activity");
    expect(areaForPath("/settings", modules())?.id).toBe("system");
  });

  it("hiçbir alana ait olmayan yüzeyler (triyaj akışı, sağlık, belgeler) satır tutmaz", () => {
    expect(areaForPath("/inbox", modules())).toBeUndefined();
    expect(areaForPath("/bilinmeyen", modules())).toBeUndefined();
    // Kaynaklar/Sistem Durumu Ayarlar'ın altındadır, kendi sidebar satırı yok.
    expect(areaForPath("/health", modules())).toBeUndefined();
    expect(areaForPath("/sources", modules())).toBeUndefined();
    // Belgeler standalone ürün yüzeyi değil (rota compat için durur).
    expect(areaForPath("/documents", modules())).toBeUndefined();
  });

  it("alana girmeyen modül kayıtlı kalır: rota, komut ve başlık çalışır", () => {
    // Navigasyonda satır tutmamak, modülü devre dışı bırakmak DEĞİLDİR.
    expect(allRoutes().some((route) => route.path === "/inbox")).toBe(true);
    expect(allCommands().some((command) => command.id === "inbox.open")).toBe(true);
    expect(moduleForPath("/inbox")?.id).toBe("inbox");
  });

  it("her modül rotası en fazla bir alana bağlıdır", () => {
    const owners = new Map<string, string>();
    for (const area of [...areasAt("primary"), ...areasAt("system")]) {
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

  it("Kütüphane satırları kendi domainlerini korur; Belgeler artık ürün yüzeyi değil", () => {
    expect(areaRows(area("library"), modules()).map((row) => `${row.label}=${row.path}`)).toEqual([
      "Yer İmleri=/bookmarks",
      "RSS & Akış=/feed",
      "RSS Kaynakları=/rss",
      "Medya=/media",
      "Bilgi=/notes",
    ]);
    // Okuma Akışı hâlâ çalışır ama ayrı bir sidebar satırı tutmaz: akış Home'un
    // ve RSS sayfasının parçasıdır.
    expect(allRoutes().some((route) => route.path === "/feed")).toBe(true);
  });

  it("Finans, Etkinlik ve Değerlendirme artık kök hedefler (uzun kuyruk yok)", () => {
    expect(areaRows(area("finance"), modules()).map((row) => `${row.label}=${row.path}`)).toEqual([
      "Abonelikler=/finance",
    ]);
    expect(areaRows(area("activity"), modules()).map((row) => `${row.label}=${row.path}`)).toEqual([
      "Etkinlik=/activity",
    ]);
    expect(areaRows(area("review"), modules()).map((row) => `${row.label}=${row.path}`)).toEqual([
      "Değerlendirme=/review/weekly",
    ]);
  });

  it("satır derinliği ağacı ifade eder: hedef 1, hedefin alt rotası 2", () => {
    const plan = areaRows(area("plan"), modules());
    const byLabel = (label: string) => plan.find((row) => row.label === label)!;
    expect(byLabel("Görevler").depth).toBe(1);
    expect(byLabel("Haftalık plan").depth).toBe(2);
    expect(byLabel("Rutinler").depth).toBe(2);
    expect(byLabel("Takvim").depth).toBe(1);
  });

  it("Öğrenme alanı kartları ve tekrar görünümünü içerir", () => {
    const rows = areaRows(area("learning"), modules());
    expect(rows.map((row) => `${row.label}=${row.path}${row.query ? `?${row.query}` : ""}`)).toEqual([
      "Öğrenme=/learning",
      "Kartlar=/flashcard",
      "Tekrar=/learning?view=review",
    ]);
  });

  it("sistem alanı TEK satır tutar: Ayarlar", () => {
    const system = areasAt("system")[0];
    expect(areaRows(system, modules()).map((row) => row.label)).toEqual(["Ayarlar"]);
    // Kaynaklar ve Sistem Durumu rotaları yaşar, sidebar satırı tutmaz.
    expect(allRoutes().some((route) => route.path === "/health")).toBe(true);
    expect(allRoutes().some((route) => route.path === "/sources")).toBe(true);
    expect(allCommands().some((command) => command.id === "health.open")).toBe(true);
    expect(allCommands().some((command) => command.id === "sources.open")).toBe(true);
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

  it("alan biçimi: tek hedefli alan bağlantı, alt satırlı alan katlanır bölüm", () => {
    for (const id of ["home", "projects", "career", "finance", "activity", "review"]) {
      expect(areaShape(area(id), modules())).toBe("link");
    }
    for (const id of ["plan", "library", "learning"]) {
      expect(areaShape(area(id), modules())).toBe("section");
    }
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

  it("derin alt rotalarda parent alan ve satır aktif kalır", () => {
    expect(areaForPath("/projects/p-12345", modules())?.id).toBe("projects");
    const projectRow = areaRows(area("projects"), modules()).find((row) => row.path === "/projects")!;
    expect(rowIsActive(projectRow, "/projects/p-12345", new URLSearchParams())).toBe(true);

    expect(areaForPath("/opportunities/opp-999", modules())?.id).toBe("career");
    const oppRow = areaRows(area("career"), modules()).find((row) => row.path === "/opportunities")!;
    expect(rowIsActive(oppRow, "/opportunities/opp-999", new URLSearchParams())).toBe(true);
  });
});
