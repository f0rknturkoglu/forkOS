// @vitest-environment jsdom
import "@/modules";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppSidebar } from "./AppSidebar";

vi.mock("@/core/api", () => ({
  api: { get: vi.fn().mockResolvedValue([]), post: vi.fn(), patch: vi.fn(), del: vi.fn() },
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

function renderSidebar(path: string, props?: Partial<ComponentProps<typeof AppSidebar>>) {
  const onCloseMobile = vi.fn();
  const onToggleCollapsed = vi.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AppSidebar
        path={path}
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

describe("AppSidebar", () => {
  beforeEach(() => localStorage.clear());
  afterEach(cleanup);

  it("modül registry'sinden ana grupları ve bilinçli çocuk rotaları üretir", () => {
    renderSidebar("/notes");

    expect(screen.getByRole("link", { name: "Bugün" }).getAttribute("href")).toBe("#/");
    expect(screen.getByRole("link", { name: "Bilgi" }).getAttribute("aria-current")).toBe("page");
    const habitsLink = screen.getByRole("link", { name: "Rutinler" });
    expect(habitsLink.getAttribute("href")).toBe("#/habits");
    expect(habitsLink.querySelector("svg")).not.toBeNull();

    const plannerLink = screen.getByRole("link", { name: "Haftalık plan" });
    expect(plannerLink.getAttribute("href")).toBe("#/planner");
    expect(plannerLink.querySelector("svg")).not.toBeNull();

    expect(screen.getByRole("link", { name: "Odak" }).getAttribute("href")).toBe("#/pomodoro");
    expect(screen.queryByRole("button", { name: "Yeni kayıt" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Gün" })).toBeNull();
  });

  it("aktif ikincil rotayı seçer ve kapalı grubunu otomatik açar", async () => {
    renderSidebar("/sources");

    const sources = await screen.findByRole("link", { name: "Kaynaklar" });
    expect(sources.getAttribute("aria-current")).toBe("page");
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Sistem" }).getAttribute("aria-expanded")).toBe("true"),
    );
  });

  it("grup tercihlerini saklar", () => {
    renderSidebar("/notes");
    fireEvent.click(screen.getByRole("button", { name: "Yakala" }));
    expect(localStorage.getItem("forkos.sidebar.groups")).not.toContain("capture");
  });

  it("daraltilmis ray basliginda genisletme dugmesi yok — logo tek basina sigar", () => {
    renderSidebar("/notes", { collapsed: true });

    // 56px raya logo (28px) + dugme (32px) sigmaz; dugme baska yuzeye tasindi.
    expect(screen.queryByRole("button", { name: "Kenar çubuğunu genişlet" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Kenar çubuğunu daralt" })).toBeNull();
    const brand = screen.getByRole("link", { name: "forkOS Bugün" });
    expect(brand.closest("aside")?.id).toBe("app-sidebar");
  });

  it("genisken daraltma dugmesi ray kimligini bildirir", () => {
    const { onToggleCollapsed } = renderSidebar("/notes");
    const collapse = screen.getByRole("button", { name: "Kenar çubuğunu daralt" });
    expect(collapse.getAttribute("aria-controls")).toBe("app-sidebar");
    expect(collapse.getAttribute("aria-expanded")).toBe("true");
    fireEvent.click(collapse);
    expect(onToggleCollapsed).toHaveBeenCalledOnce();
  });

  it("mobil scrim üzerinden kapanır", () => {
    const { onCloseMobile } = renderSidebar("/notes", { mobileOpen: true });
    fireEvent.click(screen.getByRole("button", { name: "Kenar çubuğunu kapat" }));
    expect(onCloseMobile).toHaveBeenCalledOnce();
  });

  it("sayfa navigasyonunu iptal edilebilir uygulama olayıyla duyurur", () => {
    const preventNavigation = (event: Event) => event.preventDefault();
    window.addEventListener("forkos:before-navigation", preventNavigation);
    const { onCloseMobile } = renderSidebar("/notes");

    const link = screen.getByRole("link", { name: "Haftalık plan" });
    const click = new MouseEvent("click", { bubbles: true, cancelable: true });
    link.dispatchEvent(click);

    expect(click.defaultPrevented).toBe(true);
    expect(onCloseMobile).not.toHaveBeenCalled();
    window.removeEventListener("forkos:before-navigation", preventNavigation);
  });
});
