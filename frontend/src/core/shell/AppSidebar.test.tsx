// @vitest-environment jsdom
import "@/modules";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { allRoutes } from "@/core/registry";
import { AppSidebar } from "./AppSidebar";

const apiGet = vi.fn().mockResolvedValue([]);

vi.mock("@/core/api", () => ({
  api: { get: (...args: unknown[]) => apiGet(...args), post: vi.fn(), patch: vi.fn(), del: vi.fn() },
  qs: vi.fn(() => ""),
}));

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

const PINNED_VIEW = {
  id: "3f1c9d20-0d5c-4f7c-8f0e-2f0f0f0f0f0f",
  name: "Remote EU Backend",
  module: "opportunity",
  filter: { remote: "remote" },
  sort: null,
  pinned: true,
  position: 0,
};

function renderSidebar(path: string, search = "", props?: Partial<ComponentProps<typeof AppSidebar>>) {
  const onCloseMobile = vi.fn();
  const onToggleCollapsed = vi.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AppSidebar
        path={path}
        params={new URLSearchParams(search)}
        collapsed={false}
        mobileOpen={false}
        onToggleCollapsed={onToggleCollapsed}
        onCloseMobile={onCloseMobile}
        {...props}
      />
    </QueryClientProvider>,
  );
  return { onCloseMobile, onToggleCollapsed };
}

describe("AppSidebar — ürün navigasyonu", () => {
  beforeEach(() => {
    localStorage.clear();
    apiGet.mockReset();
    apiGet.mockResolvedValue([]);
  });
  afterEach(cleanup);

  it("modül envanteri yerine ürün alanlarını gösterir", () => {
    renderSidebar("/");

    // Alt satırı olan alanlar katlanır düğme; tek hedefli alanlar bağlantı.
    for (const label of ["Plan", "Öğrenme", "Kütüphane"]) {
      expect(screen.getByRole("button", { name: label })).toBeTruthy();
      expect(screen.queryByRole("link", { name: label })).toBeNull();
    }
    for (const [label, href] of [
      ["Home", "#/"],
      ["Projeler", "#/projects"],
      ["Kariyer", "#/opportunities"],
      ["Finans", "#/finance"],
      ["Etkinlik", "#/activity"],
      ["Değerlendirme", "#/review/weekly"],
    ] as const) {
      expect(screen.getByRole("link", { name: label }).getAttribute("href")).toBe(href);
    }
  });

  it("uzun kuyruk kavramı yok: Finans, Etkinlik ve Değerlendirme kök satır", () => {
    renderSidebar("/");

    expect(screen.queryByText("Daha fazla")).toBeNull();
    expect(screen.queryByRole("button", { name: "Daha fazla" })).toBeNull();
    expect(screen.getByRole("link", { name: "Finans" }).getAttribute("href")).toBe("#/finance");
    expect(screen.getByRole("link", { name: "Etkinlik" }).getAttribute("href")).toBe("#/activity");
    expect(screen.getByRole("link", { name: "Değerlendirme" }).getAttribute("href")).toBe("#/review/weekly");
  });

  it("sidebar kendi komut aramasını tutmaz; tek giriş üst serittedir", () => {
    renderSidebar("/");

    expect(screen.queryByText("Ara veya komut")).toBeNull();
    expect(screen.queryByText("⌘K")).toBeNull();
  });

  it("sağlık ve kaynaklar sidebar satırı tutmaz; rotaları yaşar", () => {
    renderSidebar("/");

    expect(screen.queryByRole("link", { name: "Sistem Durumu" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Kaynaklar" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Belgeler" })).toBeNull();
    expect(screen.getByRole("link", { name: "Ayarlar" }).getAttribute("href")).toBe("#/settings");
    // Modül kapatmak değil: rotalar registry'de durur.
    expect(allRoutes().some((route) => route.path === "/health")).toBe(true);
    expect(allRoutes().some((route) => route.path === "/sources")).toBe(true);
    expect(allRoutes().some((route) => route.path === "/documents")).toBe(true);
  });

  it("aktif satır mavi nokta ile değil arka plan ve ağırlıkla işaretlenir", () => {
    renderSidebar("/calendar");
    const active = screen.getByRole("link", { name: "Takvim" });

    expect(active.className).toContain("bg-surface-selected");
    expect(active.className).toContain("font-medium");
    expect(active.getAttribute("aria-current")).toBe("page");
    expect(active.querySelector(".bg-accent")).toBeNull();
    expect(active.querySelector(".rounded-full")).toBeNull();
  });

  it("temiz kurulumda SADECE kök alanlar açık: alt satırlar kapalı başlar", () => {
    renderSidebar("/");

    // Kök alanlar her zaman görünür (bağlantı ya da katlanır başlık).
    for (const label of ["Home", "Projeler", "Kariyer", "Finans", "Etkinlik", "Değerlendirme"]) {
      expect(screen.getByRole("link", { name: label })).toBeTruthy();
    }
    for (const label of ["Plan", "Öğrenme", "Kütüphane"]) {
      expect(screen.getByRole("button", { name: label })).toBeTruthy();
    }
    // Alt satırlar kapalı: sakin varsayılan. Satırlar DOM'da durur ama
    // bölgeleri `hidden`dır (klavye erişimi dışında).
    for (const [areaId, label] of [
      ["plan", "Plan"],
      ["library", "Kütüphane"],
      ["learning", "Öğrenme"],
    ] as const) {
      expect(screen.getByRole("button", { name: label }).getAttribute("aria-expanded")).toBe("false");
      expect(document.getElementById(`sidebar-area-${areaId}`)?.className).toContain("hidden");
    }
  });

  it("katlanır satır tek parça: satırın tamamı açar, ok ayrı hedef değil", () => {
    renderSidebar("/");
    const plan = screen.getByRole("button", { name: "Plan" });

    // Tek geometri: h-9 satır; içinde ayrı bir okma düğmesi yok.
    expect(plan.className).toContain("h-9");
    expect(plan.className).toContain("w-full");
    expect(screen.queryByRole("button", { name: "Plan alt satırları aç" })).toBeNull();
    expect(plan.getAttribute("aria-controls")).toBe("sidebar-area-plan");

    fireEvent.click(plan);
    expect(screen.getByRole("button", { name: "Plan" }).getAttribute("aria-expanded")).toBe("true");
  });

  it("katlanır satır gezinmez: tıklama rota değiştirmez", () => {
    const { onCloseMobile } = renderSidebar("/");
    fireEvent.click(screen.getByRole("button", { name: "Kütüphane" }));

    expect(location.hash).not.toContain("/bookmarks");
    expect(onCloseMobile).not.toHaveBeenCalled();
  });

  it("tümünü genişlet / tümünü daralt tek kontrolle çalışır", () => {
    renderSidebar("/");
    const expandAll = screen.getByRole("button", { name: "Tümünü genişlet" });

    fireEvent.click(expandAll);
    for (const label of ["Plan", "Öğrenme", "Kütüphane"]) {
      expect(screen.getByRole("button", { name: label }).getAttribute("aria-expanded")).toBe("true");
    }
    expect(JSON.parse(localStorage.getItem("forkos.sidebar.areas") ?? "[]").sort()).toEqual([
      "learning",
      "library",
      "plan",
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Tümünü daralt" }));
    for (const label of ["Plan", "Öğrenme", "Kütüphane"]) {
      expect(screen.getByRole("button", { name: label }).getAttribute("aria-expanded")).toBe("false");
    }
    expect(JSON.parse(localStorage.getItem("forkos.sidebar.areas") ?? "[]")).toEqual([]);
    // Alt rotalar hâlâ erişilebilir: satırlar DOM'da durur, yalnız gizlenir.
    expect(document.getElementById("sidebar-area-plan")?.className).toContain("hidden");
  });

  it("aktif rota kendi alanını otomatik açar", async () => {
    renderSidebar("/pomodoro");
    expect(await screen.findByRole("link", { name: "Odak" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Plan" }).getAttribute("aria-expanded")).toBe("true");

    cleanup();
    renderSidebar("/rss");
    expect(await screen.findByRole("link", { name: "RSS" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Kütüphane" }).getAttribute("aria-expanded")).toBe("true");
  });

  it("kütüphane altında Medya ve Bilgi var; Okuma Akışı ayrı satır değil", async () => {
    renderSidebar("/media");
    expect(await screen.findByRole("link", { name: "Medya" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Bilgi" }).getAttribute("href")).toBe("#/notes");
    expect(screen.queryByRole("link", { name: "Okuma Akışı" })).toBeNull();
    expect(allRoutes().some((route) => route.path === "/feed")).toBe(true);
  });

  it("alt satırlar kök satırdan hafif küçük ve girintili", async () => {
    renderSidebar("/media");
    const root = screen.getByRole("button", { name: "Kütüphane" });
    const child = await screen.findByRole("link", { name: "Medya" });

    // Kök: h-9 + 16px ikon; alt satır: h-8 + girinti + 14px ikon.
    expect(root.className).toContain("h-9");
    expect(root.querySelector("svg")?.getAttribute("width")).toBe("16");
    expect(child.className).toContain("h-8");
    expect(child.className).toContain("pl-6");
    expect(child.querySelector("svg")?.getAttribute("width")).toBe("14");
    // Ağırlık farkı okunabilirliği bozmaz: alt satır hâlâ text-meta.
    expect(child.className).toContain("text-meta");
  });

  it("üçüncü seviye (modülün alt rotası) daha derin girintili", async () => {
    renderSidebar("/planner");
    const grandchild = await screen.findByRole("link", { name: "Haftalık plan" });
    expect(grandchild.className).toContain("h-7");
    expect(grandchild.className).toContain("pl-10");
  });

  it("aktif rotayı ürün alanı seviyesinde işaretler", () => {
    renderSidebar("/calendar");

    expect(screen.getByRole("link", { name: "Takvim" }).getAttribute("aria-current")).toBe("page");
    // Plan alanı başlığı da aktif bölgede kalır (alan vurgusu).
    expect(screen.getByRole("button", { name: "Plan" }).className).toContain("bg-surface-selected");
    expect(screen.getByRole("button", { name: "Kütüphane" }).className).not.toContain("bg-surface-selected");
  });

  it("tek hedefli alan aktifken de bağlantı olarak işaretlenir", () => {
    renderSidebar("/finance");
    expect(screen.getByRole("link", { name: "Finans" }).getAttribute("aria-current")).toBe("page");
  });

  it("aç/kapa tercihini saklar (temiz kurulumda kapalı)", () => {
    renderSidebar("/");
    fireEvent.click(screen.getByRole("button", { name: "Plan" }));
    expect(localStorage.getItem("forkos.sidebar.areas")).toContain("plan");
    expect(screen.getByRole("button", { name: "Plan" }).getAttribute("aria-expanded")).toBe("true");

    fireEvent.click(screen.getByRole("button", { name: "Plan" }));
    expect(localStorage.getItem("forkos.sidebar.areas")).not.toContain("plan");
  });

  it("sabitlenmiş görünümleri hedef çalışma alanına bağlar", async () => {
    apiGet.mockImplementation((path: string) => Promise.resolve(path === "/views" ? [PINNED_VIEW] : []));
    renderSidebar("/");

    const pinned = await screen.findByRole("link", { name: "Remote EU Backend" });
    expect(pinned.getAttribute("href")).toBe(`#/opportunities?saved=${PINNED_VIEW.id}`);
  });

  it("sabitlenmiş görünümlerin sunucu sırasını korur", async () => {
    apiGet.mockImplementation((path: string) =>
      Promise.resolve(
        path === "/views"
          ? [
              { ...PINNED_VIEW, id: "a", name: "Birinci", position: 0 },
              { ...PINNED_VIEW, id: "b", name: "İkinci", position: 1 },
              { ...PINNED_VIEW, id: "c", name: "Üçüncü", position: 2 },
            ]
          : [],
      ),
    );
    renderSidebar("/");

    await screen.findByRole("link", { name: "Üçüncü" });
    const labels = screen
      .getAllByRole("link")
      .map((link) => link.textContent)
      .filter((label) => label === "Birinci" || label === "İkinci" || label === "Üçüncü");
    expect(labels).toEqual(["Birinci", "İkinci", "Üçüncü"]);
  });

  it("hedefi bilinmeyen sabitlenmiş görünüm sidebar'ı çökertmez", async () => {
    apiGet.mockImplementation((path: string) =>
      Promise.resolve(path === "/views" ? [{ ...PINNED_VIEW, module: "silinmis-modul" }] : []),
    );
    renderSidebar("/");

    // Hedef modul kapaliysa satir tiklanabilir olmaz: sessizce Home'a dusmez.
    await screen.findByText("Remote EU Backend");
    expect(screen.queryByRole("link", { name: "Remote EU Backend" })).toBeNull();
  });

  it("daraltilmis ray basliginda genisletme dugmesi yok — logo tek basina sigar", () => {
    renderSidebar("/", "", { collapsed: true });

    // 56px raya logo (28px) + dugme (32px) sigmaz; dugme baska yuzeye tasindi.
    expect(screen.queryByRole("button", { name: "Kenar çubuğunu genişlet" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Kenar çubuğunu daralt" })).toBeNull();
    expect(screen.getByRole("link", { name: "forkOS Home" }).closest("aside")?.id).toBe("app-sidebar");
  });

  it("genisken daraltma dugmesi ray kimligini bildirir", () => {
    const { onToggleCollapsed } = renderSidebar("/");
    const collapse = screen.getByRole("button", { name: "Kenar çubuğunu daralt" });
    expect(collapse.getAttribute("aria-controls")).toBe("app-sidebar");
    expect(collapse.getAttribute("aria-expanded")).toBe("true");
    fireEvent.click(collapse);
    expect(onToggleCollapsed).toHaveBeenCalledOnce();
  });

  it("mobil scrim üzerinden kapanır", () => {
    const { onCloseMobile } = renderSidebar("/", "", { mobileOpen: true });
    fireEvent.click(screen.getByRole("button", { name: "Kenar çubuğunu kapat" }));
    expect(onCloseMobile).toHaveBeenCalledOnce();
  });

  it("sayfa navigasyonunu iptal edilebilir uygulama olayıyla duyurur", () => {
    const preventNavigation = (event: Event) => event.preventDefault();
    window.addEventListener("forkos:before-navigation", preventNavigation);
    const { onCloseMobile } = renderSidebar("/");

    const link = screen.getByRole("link", { name: "Haftalık plan" });
    const click = new MouseEvent("click", { bubbles: true, cancelable: true });
    link.dispatchEvent(click);

    expect(click.defaultPrevented).toBe(true);
    expect(onCloseMobile).not.toHaveBeenCalled();
    window.removeEventListener("forkos:before-navigation", preventNavigation);
  });

  it("daraltılmış ray modunda katlanır alana tıklayınca flyout menü açılır", () => {
    renderSidebar("/", "", { collapsed: true });
    const planBtn = screen.getByRole("button", { name: "Plan" });

    expect(screen.queryByRole("menu", { name: "Plan menüsü" })).toBeNull();
    fireEvent.click(planBtn);

    const menu = screen.getByRole("menu", { name: "Plan menüsü" });
    expect(menu).toBeTruthy();
    expect(screen.getByRole("menuitem", { name: "Görevler" })).toBeTruthy();
    expect(screen.getByRole("menuitem", { name: "Haftalık plan" })).toBeTruthy();
    expect(screen.getByRole("menuitem", { name: "Takvim" })).toBeTruthy();
    expect(screen.getByRole("menuitem", { name: "Odak" })).toBeTruthy();
  });

  it("daraltılmış ray modunda klavye (Enter / Escape) ile flyout kontrol edilir", () => {
    renderSidebar("/", "", { collapsed: true });
    const planBtn = screen.getByRole("button", { name: "Plan" });

    // Enter ile aç
    fireEvent.keyDown(planBtn, { key: "Enter" });
    expect(screen.getByRole("menu", { name: "Plan menüsü" })).toBeTruthy();

    // Escape ile kapat
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("menu", { name: "Plan menüsü" })).toBeNull();
  });

  it("daraltılmış ray modunda aktif alt rota alan butonunu vurgular", () => {
    renderSidebar("/calendar", "", { collapsed: true });
    const planBtn = screen.getByRole("button", { name: "Plan" });
    expect(planBtn.className).toContain("bg-surface-selected");
  });
});
