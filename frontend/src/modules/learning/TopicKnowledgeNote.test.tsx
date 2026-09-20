// @vitest-environment jsdom
/**
 * TopicKnowledgeNote — konunun kanonik bilgi notu.
 *
 * Kabul kriterleri: var olan not `getVaultItem` ile COZULUR (yeniden
 * olusturulmaz), yok ise `ensure` ile olusturulur ve Obsidian'da acilir,
 * `Vault'ta ara` arama URI'sini OS'e devreder. Eski `/notes` uclarina HIC
 * istek gitmez; govde editoru yoktur.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { ToastProvider } from "@/core/ui";
import { TopicKnowledgeNote } from "./TopicKnowledgeNote";

const harness = vi.hoisted(() => ({
  status: null as unknown,
  item: null as unknown,
  ensured: null as unknown,
  searchUri: null as unknown,
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  open: vi.fn(),
}));

vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/obsidian", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/obsidian")>();
  return { ...actual, openObsidianUri: (uri: string) => harness.open(uri) };
});
vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return { ...actual, api: { get: harness.apiGet, post: harness.apiPost } };
});

const vaultItem = {
  forkos_id: "t1",
  forkos_type: "topic",
  title: "Versiyon Kontrol Temelleri",
  relative_path: "30 Learning/Versiyon Kontrol Temelleri.md",
  open_uri: "obsidian://open?vault=Vault&file=30%20Learning%2FVersiyon%20Kontrol%20Temelleri",
  mtime: 42,
  size: 512,
  note_kind: "topic",
  entity_type: "topic",
  project_id: null,
  journal_day: null,
  source_bookmark_id: null,
  relation_count: 0,
};

const SEARCH_URI = "obsidian://search?vault=Vault&query=Versiyon+Kontrol+Temelleri";

function renderNote(topicTitle = "Versiyon Kontrol Temelleri") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <TopicKnowledgeNote topicId="t1" topicTitle={topicTitle} />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

const requestedPaths = () =>
  [...harness.apiGet.mock.calls, ...harness.apiPost.mock.calls].map(([path]) => String(path));

describe("TopicKnowledgeNote", () => {
  beforeEach(() => {
    harness.status = { configured: true, available: true, writable: true, vault_name: "Vault" };
    harness.item = vaultItem;
    harness.ensured = vaultItem;
    harness.searchUri = { uri: SEARCH_URI };
    harness.open.mockReset();
    vi.mocked(invalidateAfter).mockReset();
    harness.apiGet.mockReset();
    harness.apiPost.mockReset();

    harness.apiGet.mockImplementation(async (path: string) => {
      if (path === "/obsidian/status") return harness.status;
      if (path === "/obsidian/items/t1") {
        if (!harness.item) throw new ApiError(404, "bulunamadi", null);
        return harness.item;
      }
      if (path.startsWith("/obsidian/uri/search")) return harness.searchUri;
      throw new ApiError(404, `beklenmeyen istek: ${path}`, null);
    });
    harness.apiPost.mockImplementation(async (path: string) => {
      if (path === "/obsidian/ensure") return harness.ensured;
      throw new ApiError(404, `beklenmeyen istek: ${path}`, null);
    });
  });

  afterEach(cleanup);

  it("var olan bilgi notunu cozer, baslik/yol ve acma baglantisini gosterir", async () => {
    renderNote();

    expect(await screen.findByText(vaultItem.title)).toBeTruthy();
    expect(screen.getByText(vaultItem.relative_path)).toBeTruthy();
    const link = screen.getByRole("link", { name: /Obsidian'da aç/i });
    expect(link.getAttribute("href")).toBe(vaultItem.open_uri);

    // Cozum var olan dosyayi KULLANIR: ensure cagrilmaz.
    expect(harness.apiGet).toHaveBeenCalledWith("/obsidian/items/t1");
    expect(harness.apiPost).not.toHaveBeenCalled();
  });

  it("not yoksa `ensure` ile olusturur, tazeler ve acar; ikinci olusturma imkani kalmaz", async () => {
    harness.item = null;
    renderNote();

    const button = await screen.findByRole("button", { name: /Bilgi notu oluştur/i });
    // Not sorgusu kapanana kadar buton kapali: tiklamadan once acilmasini bekle.
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(button);

    await waitFor(() => expect(harness.apiPost).toHaveBeenCalledWith("/obsidian/ensure", { forkos_id: "t1" }));
    expect(harness.apiPost).toHaveBeenCalledTimes(1);
    expect(invalidateAfter).toHaveBeenCalledWith("obsidian.write");
    expect(harness.open).toHaveBeenCalledWith(vaultItem.open_uri);

    // Not artik cozulmus durumda: olusturma aksiyonu kaybolur (idempotent).
    expect(await screen.findByText(vaultItem.relative_path)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Bilgi notu oluştur/i })).toBeNull();
    expect(harness.apiPost).toHaveBeenCalledTimes(1);
  });

  it("'Vault'ta ara' arama URI'sini isletim sistemine devreder", async () => {
    renderNote();
    await screen.findByText(vaultItem.title);

    fireEvent.click(screen.getByRole("button", { name: /Vault'ta ara/i }));

    await waitFor(() =>
      expect(harness.apiGet).toHaveBeenCalledWith("/obsidian/uri/search?q=Versiyon+Kontrol+Temelleri"),
    );
    expect(harness.open).toHaveBeenCalledWith(SEARCH_URI);
  });

  it("Vault kapaliysa aksiyon yerine 'Vault kullanılamıyor' bilgisi gosterir", async () => {
    harness.status = { configured: true, available: false, writable: false, vault_name: "Vault" };
    renderNote();

    expect(await screen.findByText(/Vault kullanılamıyor/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Bilgi notu oluştur/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /Vault'ta ara/i })).toBeNull();
    expect(harness.apiPost).not.toHaveBeenCalled();
  });

  it("yalniz Vault uclarina gider: eski /notes istegi YOK", async () => {
    harness.item = null;
    renderNote();
    const create = await screen.findByRole("button", { name: /Bilgi notu oluştur/i });
    await waitFor(() => expect((create as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(create);
    await waitFor(() => expect(harness.apiPost).toHaveBeenCalled());
    const search = screen.getByRole("button", { name: /Vault'ta ara/i });
    await waitFor(() => expect((search as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(search);
    await waitFor(() => expect(harness.open).toHaveBeenCalled());

    const paths = requestedPaths();
    expect(paths.length).toBeGreaterThan(0);
    for (const path of paths) expect(path.startsWith("/obsidian/")).toBe(true);
    expect(paths.some((path) => path.includes("notes"))).toBe(false);
    // Govde editoru yok: yazma yuzeyi Obsidian'in kendisi.
    expect(screen.queryByRole("textbox")).toBeNull();
  });
});
