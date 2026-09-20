// @vitest-environment jsdom
/**
 * KnowledgePage — Bilgi Kasası (Vault köprüsü).
 *
 * Kabul kriterleri: dört açma eylemi de URI'yi SUNUCUDAN alıp OS'e devreder,
 * Vault yoksa teshis gösterilir, çakışma/geçersiz üst veri uyarıları warn
 * tonunda listelenir ve eski `?focus=` derin bağlantısı Vault kaydına çözülür.
 * Sayfa bir not editörü DEGILDIR: markdown alanı ve graf baglantisi çizilmez.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { KnowledgePage } from "./KnowledgePage";

const harness = vi.hoisted(() => ({
  routeParams: "",
  status: null as unknown,
  item: null as unknown,
  itemError: null as unknown,
  searches: [] as string[],
  open: vi.fn(),
  refresh: vi.fn(),
  invalidate: vi.fn(),
}));

vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/app/router", () => ({
  useHashRoute: () => ({ path: "/notes", params: new URLSearchParams(harness.routeParams) }),
}));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/core/obsidian", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/obsidian")>();
  return {
    ...actual,
    getVaultStatus: () => Promise.resolve(harness.status),
    getVaultItem: () => (harness.itemError ? Promise.reject(harness.itemError) : Promise.resolve(harness.item)),
    refreshVaultIndex: () => harness.refresh(),
    getVaultSearchUri: (query: string) => {
      harness.searches.push(query);
      return Promise.resolve({ uri: `obsidian://search?vault=f0rknbrain&query=${encodeURIComponent(query)}` });
    },
    openObsidianUri: (uri: string) => harness.open(uri),
  };
});

const healthyStatus = {
  configured: true,
  available: true,
  writable: true,
  readable: true,
  vault_name: "f0rknbrain",
  managed_files: 42,
  conflicts: 0,
  conflict_details: {},
  invalid_files: [] as string[],
  diagnostic: null,
  open_uri: "obsidian://open?vault=f0rknbrain",
  inbox_uri: "obsidian://open?vault=f0rknbrain&file=00%20Inbox",
  daily_uri: "obsidian://daily?vault=f0rknbrain",
};

const FOCUS_ID = "11111111-2222-3333-4444-555555555555";

const vaultItem = {
  forkos_id: FOCUS_ID,
  forkos_type: "note",
  title: "Zincir kuralı",
  relative_path: "30 Notes/Zincir kuralı.md",
  open_uri: "obsidian://open?vault=f0rknbrain&file=30%20Notes%2FZincir%20kural%C4%B1",
  mtime: 123,
  size: 42,
  note_kind: "note",
  entity_type: "note",
  project_id: null,
  journal_day: null,
  source_bookmark_id: null,
  relation_count: 2,
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <KnowledgePage />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

/** Durum sorgusu cozulene kadar bekler (yukleme iskeleti kaybolsun). */
const ready = () => screen.findByText(/yönetilen not/);

describe("KnowledgePage", () => {
  beforeEach(() => {
    harness.routeParams = "";
    harness.status = { ...healthyStatus };
    harness.item = null;
    harness.itemError = null;
    harness.searches = [];
    harness.open.mockReset();
    harness.refresh.mockReset().mockResolvedValue({ ...healthyStatus });
    harness.invalidate.mockReset();
  });

  afterEach(cleanup);

  it("kasayı tanıtır ve dört eylemi sunucudan gelen URI'lerle açar", async () => {
    renderPage();
    await ready();

    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Bilgi Kasası — f0rknbrain");
    expect(screen.getByText("42 yönetilen not")).toBeTruthy();
    expect(screen.getByText("Vault bağlı ✓")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Obsidian'ı Aç/ }));
    expect(harness.open).toHaveBeenLastCalledWith(healthyStatus.open_uri);

    fireEvent.click(screen.getByRole("button", { name: "Inbox" }));
    expect(harness.open).toHaveBeenLastCalledWith(healthyStatus.inbox_uri);

    fireEvent.click(screen.getByRole("button", { name: "Bugünün Notu" }));
    expect(harness.open).toHaveBeenLastCalledWith(healthyStatus.daily_uri);

    fireEvent.change(screen.getByLabelText("Vault arama sorgusu"), { target: { value: "zincir" } });
    fireEvent.click(screen.getByRole("button", { name: /Vault'ta Ara/ }));

    await waitFor(() => expect(harness.searches).toEqual(["zincir"]));
    expect(harness.open).toHaveBeenLastCalledWith("obsidian://search?vault=f0rknbrain&query=zincir");
  });

  it("indeksi yeniledikten sonra Vault sorgularını tazeler", async () => {
    renderPage();
    await ready();

    fireEvent.click(screen.getByRole("button", { name: /İndeksi yenile/ }));

    await waitFor(() => expect(harness.refresh).toHaveBeenCalledTimes(1));
    expect(harness.invalidate).toHaveBeenCalledWith("obsidian.write");
  });

  it("Vault kullanılamıyorsa teshisi gösterir ve açma eylemlerini kapatır", async () => {
    harness.status = {
      ...healthyStatus,
      configured: false,
      available: false,
      writable: false,
      readable: false,
      vault_name: "",
      managed_files: 0,
      diagnostic: "Obsidian dizini bulunamadı: /Users/x/f0rknbrain",
      open_uri: null,
      inbox_uri: null,
      daily_uri: null,
    };
    renderPage();
    await ready();

    expect(screen.getByText("Vault kullanılamıyor")).toBeTruthy();
    expect(screen.getByText("Obsidian dizini bulunamadı: /Users/x/f0rknbrain")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Obsidian'ı Aç/ }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("button", { name: "Inbox" }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("button", { name: /İndeksi yenile/ }).hasAttribute("disabled")).toBe(true);
  });

  it("kimlik çakışmasını uyarı tonunda listeler", async () => {
    harness.status = {
      ...healthyStatus,
      conflicts: 2,
      conflict_details: {
        [FOCUS_ID]: ["30 Notes/Zincir kuralı.md", "20 Projects/Eski/Zincir kuralı.md"],
        "99999999-8888-7777-6666-555555555555": ["00 Inbox/eski.md", "40 Archive/eski.md"],
      },
    };
    renderPage();
    await ready();

    expect(screen.getByText(/2 çakışma/)).toBeTruthy();
    expect(screen.getByText(/30 Notes\/Zincir kuralı\.md, 20 Projects\/Eski\/Zincir kuralı\.md/)).toBeTruthy();
    expect(screen.getByText(/00 Inbox\/eski\.md, 40 Archive\/eski\.md/)).toBeTruthy();
  });

  it("geçersiz üst verili dosyaları en fazla üç satırda gösterir", async () => {
    harness.status = {
      ...healthyStatus,
      invalid_files: ["a.md", "b.md", "c.md", "d.md", "e.md"],
    };
    renderPage();
    await ready();

    expect(screen.getByText("5 dosyada geçersiz üst veri var")).toBeTruthy();
    expect(screen.getByText("a.md")).toBeTruthy();
    expect(screen.getByText("c.md")).toBeTruthy();
    expect(screen.queryByText("d.md")).toBeNull();
    expect(screen.getByText("+2 dosya daha")).toBeTruthy();
  });

  it("eski ?focus= bağlantısını Vault kaydına çözer", async () => {
    harness.routeParams = `focus=${FOCUS_ID}`;
    harness.item = vaultItem;
    renderPage();

    expect(await screen.findByText("Taşınmış not")).toBeTruthy();
    expect(screen.getByText("Zincir kuralı")).toBeTruthy();
    expect(screen.getByText("30 Notes/Zincir kuralı.md")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Obsidian'da Aç/ }));
    expect(harness.open).toHaveBeenCalledWith(vaultItem.open_uri);
  });

  it("çözülemeyen focus için taşınmamış kayıt mesajı gösterir", async () => {
    harness.routeParams = `focus=${FOCUS_ID}`;
    harness.itemError = new Error("404");
    renderPage();

    expect(await screen.findByText("Vault'ta açılamadı")).toBeTruthy();
    expect(screen.getByText(/taşınmamış ya da yeniden adlandırılmış/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Obsidian'da Aç/ })).toBeNull();
  });

  it("focus yoksa kayıt bölümü çizilmez", async () => {
    renderPage();
    await ready();

    expect(screen.queryByText("Taşınmış not")).toBeNull();
    expect(screen.queryByText("Vault'ta açılamadı")).toBeNull();
  });

  it("not editörü ve graf bağlantısı çizmez", async () => {
    renderPage();
    await ready();

    // Markdown editörü olurdu: textarea ya da "Not içeriği" alanı.
    expect(document.querySelector("textarea")).toBeNull();
    expect(screen.queryByLabelText("Not içeriği")).toBeNull();
    // Graf yüzeyi ve rotası kaldırıldı.
    expect(screen.queryByRole("link", { name: /graf/i })).toBeNull();
    expect(document.querySelector('a[href="#/graph"]')).toBeNull();
    expect(screen.queryByRole("button", { name: /Yeni not/i })).toBeNull();
  });
});
