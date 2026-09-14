// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

type FolderFixture = (typeof mockFolders)[number];
type NoteFixture = (typeof mockNotes)[number];

function folder(id: string, name: string, parentId: string | null = null): FolderFixture {
  return { id, name, parent_id: parentId, position: 0, note_count: 0, created_at: "", updated_at: "" };
}

function note(id: string, title: string, folderId: string | null): NoteFixture {
  return {
    id,
    title,
    body: `# ${title}`,
    pinned: false,
    folder_id: folderId,
    created_at: "2026-09-01T00:00:00Z",
    updated_at: "2026-09-01T00:00:00Z",
  };
}

/** apiGet'i verilen ağaçla besler; verilmeyen kaynaklar varsayılan fixture'lardan gelir. */
function mockTree(tree: { folders?: FolderFixture[]; notes?: NoteFixture[] } = {}) {
  harness.apiGet.mockImplementation(async (path: string) => {
    if (path === "/notes") return tree.notes ?? mockNotes;
    if (path === "/note-folders") return tree.folders ?? mockFolders;
    if (path === "/projects") return [{ id: "proj-1", title: "forkOS" }];
    if (path.startsWith("/bookmarks")) return mockBookmarks;
    return [];
  });
}

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

    mockTree();
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

  it("alt klasör formu hedef klasörün içinde açılır", async () => {
    mockTree({ folders: [folder("f1", "Kasa")] });
    renderExplorer();

    const addChildBtn = await screen.findByRole("button", { name: "Kasa içine alt klasör ekle" });
    fireEvent.click(addChildBtn);

    const form = await screen.findByRole("form", { name: "Yeni alt klasör" });
    // Form, hedef klasörün alt ağacının İÇİNDE olmalı (kök form değil).
    expect(form.closest('[data-folder-id="f1"]')).not.toBeNull();

    fireEvent.change(within(form).getByLabelText("Yeni alt klasör adı"), { target: { value: "Alt" } });
    fireEvent.click(within(form).getByRole("button", { name: "Ekle" }));

    await waitFor(() =>
      expect(harness.apiPost).toHaveBeenCalledWith("/note-folders", { name: "Alt", parent_id: "f1" }),
    );
  });

  it("Tümünü daralt mount edilmiş klasörleri de kapatır", async () => {
    mockTree({ folders: [folder("f1", "Kasa")], notes: [note("n1", "Not başlığı", "f1")] });
    renderExplorer();

    expect(await screen.findByText("Not başlığı")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Tümünü daralt" }));
    expect(screen.queryByText("Not başlığı")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Tümünü genişlet" }));
    expect(await screen.findByText("Not başlığı")).toBeTruthy();
  });

  it("Tümünü daralt odaklı notu olan klasörü de kapatır", async () => {
    mockTree({ folders: [folder("f1", "Kasa")], notes: [note("n1", "Not başlığı", "f1")] });
    renderExplorer({ focusId: "n1" });

    expect(await screen.findByText("Not başlığı")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Tümünü daralt" }));
    expect(screen.queryByText("Not başlığı")).toBeNull();
  });
});
