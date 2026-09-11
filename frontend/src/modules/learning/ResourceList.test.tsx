// @vitest-environment jsdom
/**
 * ResourceList — kaynak ekle/duzenle/sil/sirala/tamamla + yer iminden baglama.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DialogHost } from "@/core/dialog";
import { ToastProvider } from "@/core/ui";
import { resourceBody, ResourceList, swapPositions } from "./ResourceList";

const harness = vi.hoisted(() => ({
  apiDel: vi.fn(),
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
}));

vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return {
    ...actual,
    api: { del: harness.apiDel, get: harness.apiGet, patch: harness.apiPatch, post: harness.apiPost },
  };
});
vi.mock("@/core/invalidation", () => ({ invalidateAfter: (...events: string[]) => harness.invalidate(...events) }));
vi.mock("@/app/router", () => ({
  navigate: vi.fn(),
  useHashRoute: () => ({ path: "/learning", params: new URLSearchParams() }),
}));
vi.mock("@/lib/hooks", () => ({
  useOnline: () => true,
  useDebounced: <T,>(value: T) => value,
}));

const resources = [
  {
    id: "r1",
    topic_id: "t1",
    title: "Pro Git",
    url: "https://git-scm.com/book",
    kind: "book",
    position: 0,
    completed_at: null,
    note: null,
    estimated_min: 30,
    last_opened_at: null,
    source: "manual",
    bookmark_id: null,
    course_id: null,
  },
  {
    id: "r2",
    topic_id: "t1",
    title: "Git ders 2",
    url: null,
    kind: "video",
    position: 1,
    completed_at: "2026-09-01T10:00:00Z",
    note: null,
    estimated_min: null,
    last_opened_at: null,
    source: "manual",
    bookmark_id: null,
    course_id: null,
  },
];

function renderList() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <DialogHost />
        <ResourceList topicId="t1" />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("resourceBody / swapPositions", () => {
  it("bos alanlari null'a cevirir, tahmini sureyi sayiya", () => {
    expect(resourceBody({ title: "  Pro Git ", url: "  ", kind: "book", note: " ", estimatedMin: 0 })).toEqual({
      title: "Pro Git",
      url: null,
      kind: "book",
      note: null,
      estimated_min: null,
    });
    expect(
      resourceBody({ title: "X", url: "https://a", kind: "link", note: "n", estimatedMin: 25 }).estimated_min,
    ).toBe(25);
  });

  it("komsu konumlari takas eder", () => {
    const items = [
      { id: "a", position: 0 },
      { id: "b", position: 1 },
    ];
    expect(swapPositions(items, 0, 1)).toEqual([
      { id: "a", position: 1 },
      { id: "b", position: 0 },
    ]);
  });

  it("konumlar esitse (eski veri) hedefin bir adim otesine yazar", () => {
    const items = [
      { id: "a", position: 0 },
      { id: "b", position: 0 },
    ];
    expect(swapPositions(items, 1, -1)).toEqual([
      { id: "b", position: -1 },
      { id: "a", position: 0 },
    ]);
  });

  it("kenarda tasma uretmez", () => {
    expect(swapPositions([{ id: "a", position: 0 }], 0, -1)).toEqual([]);
  });
});

describe("ResourceList", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.apiPost.mockReset();
    harness.apiPatch.mockReset();
    harness.apiDel.mockReset();
    harness.invalidate.mockReset();
    harness.apiGet.mockImplementation(async (path: string) => {
      if (path === "/study/topics/t1/resources") return resources;
      if (path === "/study/topics/t1/progress") return { total: 3, done: 1, pct: 33 };
      if (path.startsWith("/bookmarks")) return [{ id: "b1", title: "Yer imi: Git", url: "https://example.com/git" }];
      return [];
    });
  });

  afterEach(cleanup);

  it("ilerlemeyi backend pct'i ile cizer (frontend kendi yuzdesini hesaplamaz)", async () => {
    renderList();
    const bar = await screen.findByRole("progressbar", { name: "Öğrenme ilerlemesi" });
    expect(bar.getAttribute("aria-valuenow")).toBe("33");
    expect(screen.getByText("1/3 · %33")).toBeTruthy();
    expect(screen.getByText("Pro Git")).toBeTruthy();
    expect(screen.getByText("30 dk")).toBeTruthy();
  });

  it("tamamlandi isaretleme PATCH + learning/study tazelemesi yapar", async () => {
    renderList();
    fireEvent.click(await screen.findByRole("button", { name: "Pro Git tamamlandı olarak işaretle" }));
    await waitFor(() => expect(harness.apiPatch).toHaveBeenCalledWith("/learning/resources/r1", { completed: true }));
    expect(harness.invalidate).toHaveBeenCalledWith("learning.write", "study.write");
  });

  it("yukari/asagi siralamada iki komsunun position'i takas edilir", async () => {
    renderList();
    fireEvent.click((await screen.findAllByRole("button", { name: "Aşağı taşı" }))[0]);
    await waitFor(() => expect(harness.apiPatch).toHaveBeenCalledTimes(2));
    expect(harness.apiPatch).toHaveBeenCalledWith("/learning/resources/r1", { position: 1 });
    expect(harness.apiPatch).toHaveBeenCalledWith("/learning/resources/r2", { position: 0 });
  });

  it("silme onaydan sonra DELETE atar", async () => {
    renderList();
    const removeButtons = await screen.findAllByRole("button", { name: "Kaynağı sil" });
    fireEvent.click(removeButtons[0]);
    const dialog = await screen.findByRole("alertdialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Sil" }));
    await waitFor(() => expect(harness.apiDel).toHaveBeenCalledWith("/learning/resources/r1"));
  });

  it("duzenleme formu PATCH gonderir", async () => {
    renderList();
    fireEvent.click((await screen.findAllByRole("button", { name: "Kaynağı düzenle" }))[1]);
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Başlık"), { target: { value: "Git ders 2 (yeni)" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kaydet" }));
    await waitFor(() =>
      expect(harness.apiPatch).toHaveBeenCalledWith("/learning/resources/r2", {
        title: "Git ders 2 (yeni)",
        url: null,
        kind: "video",
        note: null,
        estimated_min: null,
      }),
    );
  });

  it("dis aksiyon sinyali formu acar (sekme zaten acikken de)", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const view = (signal: number) => (
      <QueryClientProvider client={client}>
        <ToastProvider>
          <ResourceList topicId="t1" addSignal={signal} />
        </ToastProvider>
      </QueryClientProvider>
    );
    const { rerender } = render(view(0));
    await screen.findByText("Pro Git");
    expect(screen.queryByRole("dialog")).toBeNull();

    rerender(view(1));
    expect(await screen.findByRole("dialog")).toBeTruthy();
    // Kapatildiktan sonra sinyal yeniden artarsa tekrar acilir.
    fireEvent.click(screen.getByRole("button", { name: "Kapat" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    rerender(view(2));
    expect(await screen.findByRole("dialog")).toBeTruthy();
  });

  it("yer iminden kaynak baglar; zaten bagliysa 'zaten bagli' der", async () => {
    harness.apiPost.mockResolvedValueOnce({ id: "r9", title: "Yer imi: Git" });
    renderList();
    fireEvent.click(await screen.findByRole("button", { name: /Kaynak ekle/ }));
    const dialog = await screen.findByRole("dialog");
    const bookmark = await within(dialog).findByRole("button", { name: /Yer imi: Git/ });
    fireEvent.click(bookmark);

    await waitFor(() =>
      expect(harness.apiPost).toHaveBeenCalledWith("/study/resources/attach-bookmark", {
        topic_id: "t1",
        bookmark_id: "b1",
      }),
    );
    expect(await screen.findByText('"Yer imi: Git" yer iminden eklendi.')).toBeTruthy();

    // Ayni yer imi tekrar secilirse backend mevcut kaydi doner -> uyari.
    harness.apiPost.mockResolvedValueOnce({ id: "r1", title: "Yer imi: Git" });
    fireEvent.click(await screen.findByRole("button", { name: /Yer imi: Git/ }));
    expect(await screen.findByText("Bu yer imi zaten bu konuya bağlı.")).toBeTruthy();
  });
});
