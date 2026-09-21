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

  it("varsayılan açık alanların alt satırlarını ve sistem bölümünü render eder", () => {
    renderSidebar("/");

    expect(screen.getByRole("link", { name: "Haftalık plan" }).getAttribute("href")).toBe("#/planner");
    expect(screen.getByRole("link", { name: "Rutinler" }).getAttribute("href")).toBe("#/habits");
    expect(screen.getByRole("link", { name: "Medya" }).getAttribute("href")).toBe("#/media");
    expect(screen.getByRole("link", { name: "Bilgi" }).getAttribute("href")).toBe("#/notes");
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

  it("kapatılan alanı tercih olarak saklar", () => {
    renderSidebar("/");
    fireEvent.click(screen.getByRole("button", { name: /Plan alt satırları/ }));
    expect(localStorage.getItem("forkos.sidebar.areas")).not.toContain("plan");
  });

  it("sabitlenmiş görünümleri hedef çalışma alanına bağlar", async () => {
    apiGet.mockImplementation((path: string) =>
      Promise.resolve(path === "/views" ? [PINNED_VIEW] : []),
    );
    renderSidebar("/");

    const pinned = await screen.findByRole("link", { name: "Remote EU Backend" });
    expect(pinned.getAttribute("href")).toBe(`#/opportunities?saved=${PINNED_VIEW.id}`);
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
