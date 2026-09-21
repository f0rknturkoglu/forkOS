// @vitest-environment jsdom
import "@/modules";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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

    for (const label of ["Home", "Plan", "Projeler", "Kariyer", "Öğrenme", "Kütüphane"]) {
      expect(screen.getByRole("link", { name: label })).not.toBeNull();
    }
    // Birincil alan satırları kendi başlıklarıyla gelir; modül adları alan
    // içinde yaşar (ör. Medya ve Bilgi Kütüphane altında).
    expect(screen.getByRole("link", { name: "Home" }).getAttribute("href")).toBe("#/");
    expect(screen.getByRole("link", { name: "Kariyer" }).getAttribute("href")).toBe("#/opportunities");
  });

  it("temiz kurulumda SADECE kök alanlar açık: alt satırlar kapalı başlar", () => {
    renderSidebar("/");

    // Kök alanlar her zaman görünür.
    for (const label of ["Home", "Plan", "Projeler", "Kariyer", "Öğrenme", "Kütüphane"]) {
      expect(screen.getByRole("link", { name: label })).toBeTruthy();
    }
    // Alt satırlar kapalı: sakin varsayılan. Satırlar DOM'da durur ama
    // bölgeleri `hidden`dır (klavye erişimi dışında).
    for (const [areaId, label] of [
      ["plan", "Plan"],
      ["library", "Kütüphane"],
      ["learning", "Öğrenme"],
      ["longtail", "Daha fazla"],
    ] as const) {
      expect(screen.getByRole("button", { name: `${label} alt satırları aç` }).getAttribute("aria-expanded")).toBe(
        "false",
      );
      expect(document.getElementById(`sidebar-area-${areaId}`)?.className).toContain("hidden");
    }
  });

  it("aktif rota kendi alanını otomatik açar", async () => {
    renderSidebar("/calendar");
    expect(await screen.findByRole("link", { name: "Takvim" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Plan alt satırları kapat" }).getAttribute("aria-expanded")).toBe("true");

    cleanup();
    renderSidebar("/media");
    expect(await screen.findByRole("link", { name: "Medya" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Kütüphane alt satırları kapat" })).toBeTruthy();

    cleanup();
    renderSidebar("/activity/heatmap");
    expect(await screen.findByRole("link", { name: "Isı Haritası" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Daha fazla alt satırları kapat" })).toBeTruthy();
  });

  it("kütüphane altında Okuma Akışı ve Bilgi, uzun kuyrukta Isı Haritası var", async () => {
    renderSidebar("/media");
    expect(await screen.findByRole("link", { name: "Okuma Akışı" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Okuma Akışı" }).getAttribute("href")).toBe("#/feed");
    expect(screen.getByRole("link", { name: "Bilgi" }).getAttribute("href")).toBe("#/notes");

    cleanup();
    renderSidebar("/activity");
    const heatmap = await screen.findByRole("link", { name: "Isı Haritası" });
    expect(heatmap.getAttribute("href")).toBe("#/activity/heatmap");
  });

  it("alt satırlar kök satırdan hafif küçük ve girintili", async () => {
    renderSidebar("/media");
    const root = screen.getByRole("link", { name: "Kütüphane" });
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

  it("sistem bölümü kök satır olarak kalır", () => {
    renderSidebar("/");
    expect(screen.getByRole("link", { name: "Sistem Durumu" }).getAttribute("href")).toBe("#/health");
    expect(screen.getByRole("link", { name: "Ayarlar" }).getAttribute("href")).toBe("#/settings");
  });

  it("aktif rotayı ürün alanı seviyesinde işaretler", () => {
    renderSidebar("/calendar");

    expect(screen.getByRole("link", { name: "Takvim" }).getAttribute("aria-current")).toBe("page");
    // Plan alanı etiketi de aktif bölgede kalır (alan vurgusu).
    expect(screen.getByRole("link", { name: "Plan" }).className).toContain("bg-surface-selected");
    expect(screen.getByRole("link", { name: "Kütüphane" }).className).not.toContain("bg-surface-selected");
  });

  it("uzun kuyruk alanı kapalıyken satır tutmaz, aktif rotada açılır", async () => {
    renderSidebar("/finance");

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Daha fazla alt satırları kapat" }).getAttribute("aria-expanded")).toBe(
        "true",
      ),
    );
    expect(screen.getByRole("link", { name: "Finans" }).getAttribute("aria-current")).toBe("page");
  });

  it("aç/kapa tercihini saklar (temiz kurulumda kapalı)", () => {
    renderSidebar("/");
    fireEvent.click(screen.getByRole("button", { name: "Plan alt satırları aç" }));
    expect(localStorage.getItem("forkos.sidebar.areas")).toContain("plan");
    expect(screen.getByRole("button", { name: "Plan alt satırları kapat" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Plan alt satırları kapat" }));
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
});
