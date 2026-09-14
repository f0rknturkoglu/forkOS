// @vitest-environment jsdom
/**
 * NotesPage draft korumasi: arka plan refetch'i secili notun YENI nesnesini
 * getirdiginde kaydedilmemis duzenleme uzerine sessizce yazilmaz.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NotesPage, attachmentMarkdown, insertMarkdownAt, removeAttachmentMarkdown } from "./NotesPage";
import { NOTE_NAVIGATION_EVENT } from "./noteNavigation";

vi.mock("@/core/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  qs: vi.fn(() => ""),
}));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/core/dialog", () => ({
  confirmDialog: vi.fn().mockResolvedValue(false),
}));
vi.mock("@/lib/hooks", () => ({
  useDebounced: (value: string) => value,
  useOnline: () => true,
}));
vi.mock("@/app/router", () => ({
  navigate: vi.fn(),
  useHashRoute: () => ({ params: new URLSearchParams() }),
}));
vi.mock("./NoteCanvas", () => ({
  default: () => <div aria-label="Not tuvali">Tuval</div>,
}));

import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";

const apiGet = vi.mocked(api.get);
const confirmMock = vi.mocked(confirmDialog);

const notes = [
  {
    id: "n1",
    title: "İlk not",
    body: "# Birinci\n\ngövde 1",
    pinned: false,
    created_at: "2026-08-01T09:00:00.000Z",
    updated_at: "2026-08-01T10:00:00.000Z",
    resolved_links: [],
    unresolved_links: [],
    attachments: [],
  },
  {
    id: "n2",
    title: "İkinci not",
    body: "# İkinci\n\ngövde 2",
    pinned: false,
    created_at: "2026-08-02T09:00:00.000Z",
    updated_at: "2026-08-02T10:00:00.000Z",
    resolved_links: [],
    unresolved_links: [],
    attachments: [],
  },
  {
    id: "p1",
    title: "Proje günlüğü",
    body: "# Proje notu\n\nkarar",
    pinned: false,
    project_id: "project-1",
    journal_day: "2026-09-04",
    created_at: "2026-09-04T09:00:00.000Z",
    updated_at: "2026-09-04T10:00:00.000Z",
    resolved_links: [],
    unresolved_links: [],
    attachments: [],
  },
];

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <NotesPage />
    </QueryClientProvider>,
  );
  return client;
}

describe("NotesPage draft korumasi", () => {
  beforeEach(() => {
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: {
        getItem: vi.fn(() => null),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
      },
    });
    apiGet.mockReset();
    apiGet.mockImplementation(async (path: string) => {
      if (path === "/notes") return notes;
      if (path === "/projects") return [{ id: "project-1", title: "forkOS", status: "active" }];
      return [];
    });
  });
  afterEach(cleanup);

  it("secili notun gövdesini draft olarak yukler", async () => {
    renderPage();

    const textarea = (await screen.findByLabelText("Not içeriği")) as HTMLTextAreaElement;
    expect(textarea.value).toBe("# Birinci\n\ngövde 1");
  });

  it("yazma ve render görünümünü aynı panelde değiştirir", async () => {
    renderPage();
    expect(await screen.findByLabelText("Not içeriği")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Önizle" }));
    expect(screen.queryByLabelText("Not içeriği")).toBeNull();
    expect(screen.getByRole("heading", { name: "Birinci" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Yaz" }));
    expect(screen.getByLabelText("Not içeriği")).toBeTruthy();
  });

  it("tuval görünümünde seçili notun detay sahnesini yükler", async () => {
    apiGet.mockImplementation(async (path: string) => {
      if (path === "/notes") return notes;
      if (path === "/projects") return [];
      if (path === "/notes/n1") return { ...notes[0], canvas_state: { elements: [] } };
      return [];
    });
    renderPage();
    await screen.findByLabelText("Not içeriği");

    fireEvent.click(screen.getByRole("button", { name: "Tuval" }));
    expect(await screen.findByLabelText("Not tuvali")).toBeTruthy();
    expect(apiGet).toHaveBeenCalledWith("/notes/n1");
  });

  it("ikinci bir not rayı üretmeden seçili notu tam çalışma alanında gösterir", async () => {
    renderPage();
    expect(await screen.findByLabelText("Not içeriği")).toBeTruthy();
    expect(screen.queryByText("Kişisel notlar")).toBeNull();
    expect(screen.queryByText("Proje notları")).toBeNull();
  });

  it("arka plan refetch'i kaydedilmemis draft'i silmez", async () => {
    const client = renderPage();
    const textarea = (await screen.findByLabelText("Not içeriği")) as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: "KAYDEDİLMEMİŞ TASLAK" } });
    expect(textarea.value).toBe("KAYDEDİLMEMİŞ TASLAK");

    // Refetch ayni notun YENI nesnesini getirir (sunucudan guncel govde).
    const refetched = notes.map((note, index) => (index === 0 ? { ...note, body: "# Birinci\n\ngüncel gövde" } : note));
    apiGet.mockImplementation(async (path: string) => (path === "/notes" ? refetched : []));
    await act(async () => {
      await client.refetchQueries({ queryKey: ["notes"] });
    });

    expect(textarea.value).toBe("KAYDEDİLMEMİŞ TASLAK");
  });

  it("kaydedilmemis draft varken baska nota gecilirse onay reddedilince taslak korunur", async () => {
    confirmMock.mockResolvedValueOnce(false);
    renderPage();
    const textarea = (await screen.findByLabelText("Not içeriği")) as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: "KAYDEDİLMEMİŞ TASLAK" } });
    window.dispatchEvent(new CustomEvent(NOTE_NAVIGATION_EVENT, { detail: { kind: "open", id: "n2" } }));

    expect(confirmMock).toHaveBeenCalled();
    expect(textarea.value).toBe("KAYDEDİLMEMİŞ TASLAK");
  });

  it("kaydedilmemis draft varken onay verilince yeni notun gövdesi yuklenir", async () => {
    confirmMock.mockResolvedValueOnce(true);
    renderPage();
    const textarea = (await screen.findByLabelText("Not içeriği")) as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: "KAYDEDİLMEMİŞ TASLAK" } });
    await act(async () => {
      window.dispatchEvent(new CustomEvent(NOTE_NAVIGATION_EVENT, { detail: { kind: "open", id: "n2" } }));
    });

    expect(confirmMock).toHaveBeenCalled();
    expect(textarea.value).toBe("# İkinci\n\ngövde 2");
  });

  it("sol panelde NotesExplorer vault gezginini sunar ve gizlenip açılabilir", async () => {
    renderPage();
    expect(await screen.findByLabelText("Not içeriği")).toBeTruthy();
    expect(screen.getByText("Kasa")).toBeTruthy();
    expect(screen.getByText("Okuma Vurguları")).toBeTruthy();

    const closeBtn = screen.getByRole("button", { name: "Gezgini kapat" });
    fireEvent.click(closeBtn);
    expect(screen.queryByText("Kasa")).toBeNull();

    const openBtn = screen.getByRole("button", { name: "Kasa gezginini aç" });
    fireEvent.click(openBtn);
    expect(screen.getByText("Kasa")).toBeTruthy();
  });
});

describe("not eki markdown yerleşimi", () => {
  it("görseli imleç konumuna blok olarak yerleştirir", () => {
    const markup = attachmentMarkdown({
      id: "a1",
      name: "ekran [son].png",
      mime: "image/png",
      size: 42,
      url: "/api/notes/n1/attachments/a1",
    });
    expect(markup).toBe("![ekran son .png](/api/notes/n1/attachments/a1)");
    expect(insertMarkdownAt("önce\nsonra", 5, markup).value).toBe(
      "önce\n\n![ekran son .png](/api/notes/n1/attachments/a1)\n\nsonra",
    );
  });

  it("ses ve çizimi normal markdown eki olarak yerleştirir", () => {
    const base = { id: "a1", size: 42, url: "/api/notes/n1/attachments/a1" };
    expect(attachmentMarkdown({ ...base, name: "ses.m4a", mime: "audio/mp4" })).toBe(
      "[ses.m4a](/api/notes/n1/attachments/a1)",
    );
    expect(attachmentMarkdown({ ...base, name: "akış.excalidraw", mime: "application/vnd.excalidraw+json" })).toBe(
      "[akış.excalidraw](/api/notes/n1/attachments/a1)",
    );
  });

  it("silinen ekin markdown referansını da kaldırır", () => {
    const attachment = {
      id: "a1",
      name: "ses.m4a",
      mime: "audio/mp4",
      size: 42,
      url: "/api/notes/n1/attachments/a1",
    };
    expect(removeAttachmentMarkdown(`önce\n\n${attachmentMarkdown(attachment)}\n\nsonra`, attachment)).toBe(
      "önce\n\nsonra",
    );
  });
});
