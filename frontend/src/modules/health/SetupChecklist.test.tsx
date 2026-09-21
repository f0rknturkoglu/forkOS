// @vitest-environment jsdom
/**
 * Kurulum kontrol listesi (P6 §53).
 *
 * Kural: karmaşık sihirbaz değil. Eksik adım yoksa veya kullanıcı kapattıysa
 * yüzey HİÇ çizilmez; kurulumu tamamlanmış kullanıcıyı rahatsız etmez.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SetupChecklist } from "./SetupChecklist";

const apiGet = vi.fn();
const getVaultStatus = vi.fn();

vi.mock("@/core/api", () => ({
  api: { get: (...args: unknown[]) => apiGet(...args) },
  qs: vi.fn(() => ""),
}));
vi.mock("@/core/obsidian", () => ({
  getVaultStatus: (...args: unknown[]) => getVaultStatus(...args),
}));

const store = new Map<string, string>();
beforeEach(() => {
  store.clear();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => store.set(key, value),
      removeItem: (key: string) => store.delete(key),
      clear: () => store.clear(),
    },
  });
  apiGet.mockReset();
  getVaultStatus.mockReset();
  getVaultStatus.mockResolvedValue({ configured: true, available: true, readable: true });
});

afterEach(cleanup);

/** Eksik adım bırakan sahte yanıtlar (GitHub bağlı değil). */
function serve(overrides: { settings?: unknown; proactivity?: unknown } = {}) {
  apiGet.mockImplementation((path: string) => {
    if (path === "/auth/github/status") return Promise.resolve({ connected: false });
    if (path === "/auth/google/status") return Promise.resolve({ connected: true });
    if (path === "/settings")
      return Promise.resolve(overrides.settings ?? { "opportunity.career_profile": { current_location: "İstanbul" } });
    if (path === "/proactivity/status") return Promise.resolve(overrides.proactivity ?? { enabled: true });
    return Promise.resolve({});
  });
}

function renderChecklist() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SetupChecklist />
    </QueryClientProvider>,
  );
}

describe("SetupChecklist", () => {
  it("eksik adım varsa yalnız o adımı bağlantı olarak gösterir", async () => {
    serve();
    renderChecklist();

    const github = await screen.findByRole("link", { name: "GitHub" });
    expect(github.getAttribute("href")).toBe("#/settings?tab=integrations");
    // Tamamlanan adımlar bağlantı değil, düz metin olarak kalır.
    await waitFor(() => expect(screen.queryByRole("link", { name: "Google (Drive)" })).toBeNull());
    expect(screen.getByText("Google (Drive)")).toBeTruthy();
  });

  it("her şey hazırsa hiçbir şey çizmez", async () => {
    serve();
    apiGet.mockImplementation((path: string) =>
      Promise.resolve(
        path === "/auth/github/status" || path === "/auth/google/status"
          ? { connected: true }
          : path === "/settings"
            ? { "opportunity.career_profile": { current_location: "İstanbul" } }
            : { enabled: true },
      ),
    );
    const { container } = renderChecklist();

    await waitFor(() => expect(apiGet).toHaveBeenCalledWith("/proactivity/status"));
    await waitFor(() => expect(container.textContent).toBe(""));
  });

  it("kapatılınca kaydeder ve bir daha çizilmez", async () => {
    serve();
    const { container } = renderChecklist();

    fireEvent.click(await screen.findByRole("button", { name: "Kurulum listesini kapat" }));
    expect(store.get("forkos.setup.dismissed")).toBe("1");
    expect(container.textContent).toBe("");

    cleanup();
    renderChecklist();
    expect(screen.queryByText("Kurulum")).toBeNull();
  });

  it("kasa hazır değilse Vault adımı eksik kalır ve köprüye yönlendirir", async () => {
    getVaultStatus.mockResolvedValue({ configured: false, available: false, readable: false });
    serve();
    renderChecklist();

    const vault = await screen.findByRole("link", { name: "Bilgi kasası (Vault)" });
    expect(vault.getAttribute("href")).toBe("#/notes");
  });
});
