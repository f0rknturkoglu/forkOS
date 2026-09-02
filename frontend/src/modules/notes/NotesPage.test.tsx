// @vitest-environment jsdom
/**
 * NotesPage draft korumasi: arka plan refetch'i secili notun YENI nesnesini
 * getirdiginde kaydedilmemis duzenleme uzerine sessizce yazilmaz.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NotesPage } from "./NotesPage";

vi.mock("@/core/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  qs: vi.fn(() => ""),
}));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/lib/hooks", () => ({
  useDebounced: (value: string) => value,
  useOnline: () => true,
}));
vi.mock("@/app/router", () => ({
  navigate: vi.fn(),
  useHashRoute: () => ({ params: new URLSearchParams() }),
}));

import { api } from "@/core/api";

const apiGet = vi.mocked(api.get);

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
    apiGet.mockReset();
    apiGet.mockImplementation(async (path: string) => {
      if (path === "/notes") return notes;
      return [];
    });
  });
  afterEach(cleanup);

  it("secili notun gövdesini draft olarak yukler", async () => {
    renderPage();

    const textarea = (await screen.findByLabelText("Not içeriği")) as HTMLTextAreaElement;
    expect(textarea.value).toBe("# Birinci\n\ngövde 1");
  });

  it("arka plan refetch'i kaydedilmemis draft'i silmez", async () => {
    const client = renderPage();
    const textarea = (await screen.findByLabelText("Not içeriği")) as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: "KAYDEDİLMEMİŞ TASLAK" } });
    expect(textarea.value).toBe("KAYDEDİLMEMİŞ TASLAK");

    // Refetch ayni notun YENI nesnesini getirir (sunucudan guncel govde).
    const refetched = notes.map((note, index) =>
      index === 0 ? { ...note, body: "# Birinci\n\ngüncel gövde" } : note,
    );
    apiGet.mockImplementation(async (path: string) => (path === "/notes" ? refetched : []));
    await act(async () => {
      await client.refetchQueries({ queryKey: ["notes"] });
    });

    expect(textarea.value).toBe("KAYDEDİLMEMİŞ TASLAK");
  });

  it("not id'si degistiginde yeni notun gövdesi yuklenir", async () => {
    renderPage();
    const textarea = (await screen.findByLabelText("Not içeriği")) as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: "KAYDEDİLMEMİŞ TASLAK" } });
    fireEvent.click(screen.getByRole("button", { name: /İkinci not/ }));

    expect(textarea.value).toBe("# İkinci\n\ngövde 2");
  });
});
