// @vitest-environment jsdom
import "@/modules";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CommandPalette, openCommandPalette } from "./CommandPalette";

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("@/core/api", () => ({
  api: apiMock,
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

  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserverMock;
  window.HTMLElement.prototype.scrollIntoView = () => {};
});

function renderPalette() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <CommandPalette />
    </QueryClientProvider>,
  );
}

describe("CommandPalette v2", () => {
  beforeEach(() => {
    apiMock.get.mockReset().mockResolvedValue({});
    location.hash = "#/";
  });
  afterEach(cleanup);

  it("kapalıyken DOM'da çizilmez", () => {
    renderPalette();
    expect(screen.queryByRole("dialog", { name: "Komut paleti" })).toBeNull();
  });

  it("Cmd+K veya Ctrl+K ile açılır ve Escape ile kapanır", () => {
    renderPalette();

    // Ctrl+K ile aç
    fireEvent.keyDown(document, { key: "k", ctrlKey: true });
    expect(screen.getByPlaceholderText(/Komut, sayfa veya arama…/)).toBeTruthy();

    // Escape ile kapat
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByPlaceholderText(/Komut, sayfa veya arama…/)).toBeNull();
  });

  it("openCommandPalette olayıyla açılır", () => {
    renderPalette();
    act(() => {
      openCommandPalette();
    });
    expect(screen.getByPlaceholderText(/Komut, sayfa veya arama…/)).toBeTruthy();
  });

  it("Gezin grubu ürün alanlarını ve sayfaları listeler", () => {
    renderPalette();
    act(() => {
      openCommandPalette();
    });

    // Gezin grubu başlığı ve temel rotalar
    expect(screen.getByText("Gezin")).toBeTruthy();
    expect(screen.getByText("Projeler")).toBeTruthy();
    expect(screen.getByText("Finans")).toBeTruthy();
  });

  it("Gezin öğesi seçildiğinde rotaya gider ve paleti kapatır", () => {
    renderPalette();
    act(() => {
      openCommandPalette();
    });

    const projeler = screen.getByText("Projeler");
    fireEvent.click(projeler);

    expect(location.hash).toBe("#/projects");
    expect(screen.queryByPlaceholderText(/Komut, sayfa veya arama…/)).toBeNull();
  });

  it("Cmd+, kısayolu doğrudan Ayarlar sayfasına gider", () => {
    renderPalette();

    fireEvent.keyDown(document, { key: ",", metaKey: true });
    expect(location.hash).toBe("#/settings");
  });

  it("global varlık arama sonuçlarını gruplar halinde gösterir", async () => {
    apiMock.get.mockImplementation((path: string) => {
      if (path.startsWith("/search")) {
        return Promise.resolve({
          hits: [{ id: "proj-1", type: "project", title: "forkOS Yeniden Tasarım" }],
        });
      }
      return Promise.resolve({});
    });

    renderPalette();
    act(() => {
      openCommandPalette();
    });

    const input = screen.getByPlaceholderText(/Komut, sayfa veya arama…/);
    fireEvent.change(input, { target: { value: "forkOS" } });

    await waitFor(() => {
      expect(screen.getByText("forkOS Yeniden Tasarım")).toBeTruthy();
    });
  });
});
