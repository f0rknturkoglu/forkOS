// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NotesExplorer } from "./NotesExplorer";

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDel: vi.fn(),
  invalidate: vi.fn(),
}));

vi.mock("@/core/api", () => ({
  api: {
    get: harness.apiGet,
    post: harness.apiPost,
    patch: harness.apiPatch,
    del: harness.apiDel,
  },
}));

vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...args: unknown[]) => harness.invalidate(...args),
}));

const mockFolders = [
  { id: "f1", name: "Düşünceler", parent_id: null, position: 0, note_count: 1, created_at: "", updated_at: "" },
  { id: "f2", name: "Kitaplar", parent_id: "f1", position: 0, note_count: 1, created_at: "", updated_at: "" },
];

const mockNotes = [
  {
    id: "n1",
    title: "Kök Düşünce",
    body: "# Kök",
    pinned: false,
    folder_id: null,
    created_at: "2026-09-01T00:00:00Z",
    updated_at: "2026-09-01T00:00:00Z",
  },
  {
    id: "n2",
    title: "Düşünce Notu",
    body: "# Düşünce",
    pinned: false,
    folder_id: "f1",
    created_at: "2026-09-02T00:00:00Z",
    updated_at: "2026-09-02T00:00:00Z",
  },
  {
    id: "n3",
    title: "Kitap Özeti",
    body: "# Kitap",
    pinned: false,
    folder_id: "f2",
    created_at: "2026-09-03T00:00:00Z",
    updated_at: "2026-09-03T00:00:00Z",
  },
  {
    id: "p1",
    title: "forkOS Tasarım",
    body: "# Proje",
    pinned: false,
    project_id: "proj-1",
    created_at: "2026-09-04T00:00:00Z",
    updated_at: "2026-09-04T00:00:00Z",
  },
];

const mockBookmarks = [
  { id: "b1", title: "Makale", url: "https://example.com", selection: "Önemli bir alıntı" },
  { id: "b2", title: "Alıntısız", url: "https://example.com", selection: "" },
];

function renderExplorer(props: { focusId?: string; onSelectNote?: (id: string) => void } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <NotesExplorer focusId={props.focusId ?? ""} onSelectNote={props.onSelectNote} />
    </QueryClientProvider>,
  );
}

describe("NotesExplorer (Obsidian Vault Gezgini)", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.apiPost.mockReset();
    harness.apiPatch.mockReset();
    harness.apiDel.mockReset();
    harness.invalidate.mockReset();

    harness.apiGet.mockImplementation(async (path: string) => {
      if (path === "/notes") return mockNotes;
      if (path === "/note-folders") return mockFolders;
      if (path === "/projects") return [{ id: "proj-1", title: "forkOS" }];
      if (path.startsWith("/bookmarks")) return mockBookmarks;
      return [];
    });
  });

  afterEach(cleanup);

  it("kasa başlığı, toplam not sayısı ve akıllı vurguları listeler", async () => {
    renderExplorer();

    expect(await screen.findByText("Kök Düşünce")).toBeTruthy();
    expect(screen.getByText("Kasa")).toBeTruthy();
    expect(screen.getByText("Okuma Vurguları")).toBeTruthy();
    expect(screen.getByText("Düşünceler")).toBeTruthy();
  });

  it("klasör genişletilip daraltılabilir", async () => {
    renderExplorer();

    expect(await screen.findByText("Düşünceler")).toBeTruthy();
    const toggleBtn = screen.getByRole("button", { name: "Düşünceler klasörünü daralt" });
    fireEvent.click(toggleBtn);

    expect(screen.queryByText("Düşünce Notu")).toBeNull();
  });

  it("arama kutusu notları anında filtreler", async () => {
    renderExplorer();

    expect(await screen.findByText("Kök Düşünce")).toBeTruthy();
    const searchInput = screen.getByPlaceholderText("Notlarda filtrele...");

    fireEvent.change(searchInput, { target: { value: "kitap" } });
    expect(screen.getByText("Kitap Özeti")).toBeTruthy();
    expect(screen.queryByText("Kök Düşünce")).toBeNull();
  });

  it("satır içi yeni klasör ekleme formu çalışır", async () => {
    renderExplorer();

    expect(await screen.findByText("Kasa")).toBeTruthy();
    const addFolderBtn = screen.getByRole("button", { name: "Yeni klasör oluştur" });
    fireEvent.click(addFolderBtn);

    const folderInput = screen.getByPlaceholderText("Klasör adı...");
    fireEvent.change(folderInput, { target: { value: "Yeni Klasör" } });
    fireEvent.click(screen.getByRole("button", { name: "Ekle" }));

    await waitFor(() => {
      expect(harness.apiPost).toHaveBeenCalledWith("/note-folders", {
        name: "Yeni Klasör",
        parent_id: null,
      });
    });
  });

  it("not tıklandığında onSelectNote tetiklenir", async () => {
    const onSelect = vi.fn();
    renderExplorer({ onSelectNote: onSelect });

    expect(await screen.findByText("Kök Düşünce")).toBeTruthy();
    fireEvent.click(screen.getByText("Kök Düşünce"));

    expect(onSelect).toHaveBeenCalledWith("n1");
  });
});
