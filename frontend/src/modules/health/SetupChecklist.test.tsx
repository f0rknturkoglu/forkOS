// @vitest-environment jsdom
/**
 * Kurulum kontrol listesi (§87).
 *
 * Sözleşme: isteğe bağlı entegrasyonlar (GitHub, Google, kariyer profili,
 * proaktivite) "kurulum tamamlanmadı" SAYILMAZ. Liste yalnız ÇEKİRDEK bir adım
 * eksik/okunamaz olduğunda çizilir; eksik adım "eksik", okunamayan adım
 * "doğrulanamadı" der (bilinmiyor ≠ eksik).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SetupChecklist } from "./SetupChecklist";

const apiGet = vi.fn();
const getVaultStatus = vi.fn();

vi.mock("@/core/api", () => ({
  api: { get: (...args: unknown[]) => apiGet(...args) },
  qs: vi.fn(() => ""),
}));
vi.mock("@/core/obsidian", () => ({
  VAULT_STATUS_KEY: "vault-status",
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

interface ServeOptions {
  vault?: { configured: boolean; available: boolean; readable: boolean } | "error";
  settings?: "error" | unknown;
  github?: boolean;
  google?: boolean;
  proactivity?: boolean;
}

/** Varsayılan: çekirdek hazır, isteğe bağlı entegrasyonların hiçbiri bağlı değil. */
function serve(options: ServeOptions = {}) {
  if (options.vault === "error") getVaultStatus.mockRejectedValue(new Error("vault down"));
  else if (options.vault) getVaultStatus.mockResolvedValue(options.vault);
  apiGet.mockImplementation((path: string) => {
    if (path === "/auth/github/status") return Promise.resolve({ connected: options.github ?? false });
    if (path === "/auth/google/status") return Promise.resolve({ connected: options.google ?? false });
    if (path === "/proactivity/status") return Promise.resolve({ enabled: options.proactivity ?? false });
    if (path === "/settings") {
      if (options.settings === "error") return Promise.reject(new Error("settings down"));
      return Promise.resolve(options.settings ?? {});
    }
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
  it("yalnız isteğe bağlı entegrasyonlar eksikse liste ÇİZİLMEZ", async () => {
    serve();
    const { container } = renderChecklist();

    // Ayarlar okunana kadar beklenir; çekirdek hazır olduğu için hiçbir şey çizilmez.
    await waitFor(() => expect(apiGet).toHaveBeenCalledWith("/settings"));
    await waitFor(() => expect(container.textContent).toBe(""));
    expect(screen.queryByText("Kurulum")).toBeNull();
  });

  it("kasaya bağlı değilse çekirdek liste görünür ve köprüye yönlendirir", async () => {
    serve({ vault: { configured: false, available: false, readable: false } });
    renderChecklist();

    const vault = await screen.findByRole("link", { name: "Bilgi kasası (Vault)" });
    expect(vault.getAttribute("href")).toBe("#/settings?tab=brain");
    // İsteğe bağlı entegrasyonlar katlanmış notta durur: "eksik" gibi görünmez.
    expect(screen.queryByRole("link", { name: "GitHub" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /İsteğe bağlı entegrasyonlar/ }));
    // Satır kendi bağlantısını taşır: entegrasyon adı + Ayarlar köprüsü.
    const githubRow = (await screen.findByText("GitHub")).closest("li");
    expect(githubRow).not.toBeNull();
    const github = within(githubRow as HTMLElement).getByRole("link", { name: "Ayarlar →" });
    expect(github.getAttribute("href")).toBe("#/settings?tab=integrations");
    expect(screen.getAllByText("bağlı değil").length).toBeGreaterThan(0);
    expect(screen.queryByText("eksik")).toBeNull();
  });

  it("kasa durumu okunamazsa 'doğrulanamadı' der, eksik DEMEZ", async () => {
    serve({ vault: "error" });
    renderChecklist();

    expect(await screen.findByText("doğrulanamadı")).toBeTruthy();
    expect(screen.queryByText("eksik")).toBeNull();
  });

  it("yerel API okunamazsa çekirdek adımı 'doğrulanamadı' olarak söyler", async () => {
    serve({ settings: "error" });
    renderChecklist();

    const workspace = await screen.findByRole("link", { name: "Yerel çalışma alanı (API + veritabanı)" });
    expect(workspace.getAttribute("href")).toBe("#/health");
    expect(await screen.findByText("doğrulanamadı")).toBeTruthy();
    expect(screen.queryByText("Kurulum")).toBeTruthy();
  });

  it("kapatılınca kaydeder ve bir daha çizilmez", async () => {
    serve({ vault: { configured: false, available: false, readable: false } });
    const { container } = renderChecklist();

    fireEvent.click(await screen.findByRole("button", { name: "Kurulum listesini kapat" }));
    expect(store.get("forkos.setup.dismissed")).toBe("1");
    expect(container.textContent).toBe("");

    cleanup();
    renderChecklist();
    expect(screen.queryByText("Kurulum")).toBeNull();
  });
});
