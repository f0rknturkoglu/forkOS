// @vitest-environment jsdom
/**
 * ProjectKnowledgeNote — kanonik proje bilgi notu.
 *
 * Kabul kriterleri: yok ise `ensure` ile olusturulur (istemci baslik/tip
 * gondermez), olusan not `open_uri` ile OS'e devredilir, Vault yazmasi
 * `obsidian.write` bildirir, 409 cakismasinda olusturma kapali kalir.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/core/api";
import { ToastProvider } from "@/core/ui";
import type { Project } from "@/core/types";
import { ProjectKnowledgeNote } from "./ProjectKnowledgeNote";

const harness = vi.hoisted(() => ({
  status: null as unknown,
  item: null as unknown,
  itemError: null as unknown,
  ensureItem: vi.fn(),
  open: vi.fn(),
}));

vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/core/obsidian", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/obsidian")>();
  return {
    ...actual,
    getVaultStatus: () => Promise.resolve(harness.status),
    getVaultItem: () => (harness.itemError ? Promise.reject(harness.itemError) : Promise.resolve(harness.item)),
    ensureVaultItem: (forkosId: string) => harness.ensureItem(forkosId),
    openObsidianUri: (uri: string) => harness.open(uri),
  };
});

const mockProject: Project = {
  id: "p1111111-1111-1111-1111-111111111111",
  title: "forkOS Core",
  status: "active",
  github_repo: "f0rknturkoglu/forkOS",
  url: null,
  stack: ["python", "react"],
  next_action: null,
  last_activity_at: null,
  position: 0,
  milestones: [],
};

const vaultItem = {
  forkos_id: mockProject.id,
  forkos_type: "project",
  title: "forkOS Core",
  relative_path: "20 Projects/forkOS Core.md",
  open_uri: "obsidian://open?vault=Vault&file=20%20Projects%2FforkOS%20Core",
  mtime: 12345,
  size: 100,
  note_kind: "project",
  entity_type: "project",
  project_id: mockProject.id,
  journal_day: null,
  source_bookmark_id: null,
  relation_count: 0,
};

function renderNote() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <ProjectKnowledgeNote project={mockProject} />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("ProjectKnowledgeNote", () => {
  beforeEach(() => {
    harness.status = { configured: true, available: true, writable: true, vault_name: "Vault" };
    harness.item = null;
    harness.itemError = null;
    harness.ensureItem.mockReset();
    harness.open.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("Vault yapılandırılmamışsa bilgilendirme metni gösterir", () => {
    harness.status = { configured: false, available: false, writable: false, vault_name: "Vault" };
    renderNote();
    expect(screen.getByText(/Obsidian Vault yapılandırılmamış/)).toBeDefined();
  });

  it("Not mevcutsa başlığını, yolunu ve açma bağlantısını listeler", async () => {
    harness.item = vaultItem;
    renderNote();

    expect(await screen.findByText("forkOS Core")).toBeTruthy();
    expect(screen.getByText("20 Projects/forkOS Core.md")).toBeTruthy();
    const link = screen.getByRole("link", { name: /Obsidian'da aç/i });
    expect(link.getAttribute("href")).toBe(vaultItem.open_uri);
    // Var olan not icin yeniden olusturma cagrisi yok.
    expect(harness.ensureItem).not.toHaveBeenCalled();
  });

  it("Not yoksa `ensure` ile oluşturur, Vault'u tazeler ve notu Obsidian'da açar", async () => {
    harness.item = null;
    harness.ensureItem.mockResolvedValue(vaultItem);

    renderNote();
    const button = await screen.findByRole("button", { name: /Obsidian proje notu oluştur/i });
    // Not sorgusu kapanana kadar buton kapali: tiklamadan once acilmasini bekle.
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(button);

    await waitFor(() => expect(harness.ensureItem).toHaveBeenCalledWith(mockProject.id));
    // Istemci baslik/tip/klasor gondermez: sunucu cozer.
    expect(harness.ensureItem).toHaveBeenCalledTimes(1);
    expect(harness.open).toHaveBeenCalledWith(vaultItem.open_uri);
    expect(await screen.findByText(vaultItem.relative_path)).toBeTruthy();
    // Olusturma butonu kayboldu: ikinci bir olusturma tetiklenemez.
    expect(screen.queryByRole("button", { name: /Obsidian proje notu oluştur/i })).toBeNull();
  });

  it("Kimlik çakışması (409) varsa uyarı gösterir ve oluştur butonunu gizler", async () => {
    harness.itemError = new ApiError(409, "çakışma", null);
    renderNote();

    expect(await screen.findByText(/Bu kimlik birden fazla Obsidian dosyasında kullanılıyor/i)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Obsidian proje notu oluştur/i })).toBeNull();
    expect(harness.ensureItem).not.toHaveBeenCalled();
  });

  it("indeks çakışma kaydı varsa dosya yollarını listeler", async () => {
    harness.status = {
      configured: true,
      available: true,
      writable: true,
      vault_name: "Vault",
      conflicts: 1,
      conflict_details: {
        [mockProject.id]: ["20 Projects/forkOS Core/forkOS Core.md", "20 Projects/Old/forkOS Core.md"],
      },
    };
    renderNote();

    expect(await screen.findByText("20 Projects/forkOS Core/forkOS Core.md")).toBeTruthy();
    expect(screen.getByText("20 Projects/Old/forkOS Core.md")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Obsidian proje notu oluştur/i })).toBeNull();
  });
});
