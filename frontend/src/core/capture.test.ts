// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from "vitest";
import { capture, readCaptureKindPreference, writeCaptureKindPreference } from "./capture";
import { writePlanTodayPreference } from "./tasks";

// jsdom 30 + Node 26 localStorage getter sorunu (TodoComposer.test ile ayni).
vi.hoisted(() => {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    value: {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => {
        store.set(k, v);
      },
      removeItem: (k: string) => {
        store.delete(k);
      },
      clear: () => {
        store.clear();
      },
      key: () => null,
      get length() {
        return store.size;
      },
    },
    configurable: true,
  });
});

const harness = vi.hoisted(() => ({
  apiPost: vi.fn(),
  invalidate: vi.fn(),
}));

vi.mock("@/core/api", () => ({ api: { post: harness.apiPost } }));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/core/queryClient", () => ({ queryClient: vi.fn() }));

beforeEach(() => {
  harness.apiPost.mockReset();
  harness.invalidate.mockReset();
  localStorage.clear();
});

describe("evrensel yakalama (Faz 22)", () => {
  it("task: 'bugune al' acikken plan_day gider, due_at uretilmez", async () => {
    writePlanTodayPreference(true);
    harness.apiPost.mockResolvedValue({ id: "t1" });
    await capture({ kind: "task", text: "Raporu yaz" });
    const [path, body] = harness.apiPost.mock.calls[0];
    expect(path).toBe("/todos");
    expect(body.plan_day).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(body).not.toHaveProperty("due_at");
    expect(harness.invalidate).toHaveBeenCalledWith("todo.write", "plan.write");
  });

  it("task: tercih kapaliyken plan_day YOK", async () => {
    writePlanTodayPreference(false);
    harness.apiPost.mockResolvedValue({ id: "t1" });
    await capture({ kind: "task", text: "Raporu yaz" });
    expect(harness.apiPost.mock.calls[0][1]).not.toHaveProperty("plan_day");
  });

  it("note: TEK istek /obsidian/capture; pinned GONDERILMEZ, Vault kaydi doner", async () => {
    harness.apiPost.mockResolvedValueOnce({
      forkos_id: "vault-1",
      open_uri: "obsidian://open?vault=f0rknbrain&file=00%20Inbox%2FToplant%C4%B1",
    });
    const result = await capture({ kind: "note", text: "Toplantı notu", note: { relate_to: "opp-1" } });
    expect(harness.apiPost).toHaveBeenCalledTimes(1);
    expect(harness.apiPost).toHaveBeenCalledWith("/obsidian/capture", {
      body: "Toplantı notu",
      relate_to: "opp-1",
    });
    expect(harness.apiPost.mock.calls[0][1]).not.toHaveProperty("pinned");
    // forkOS not entity'si yazilmaz: note.write/link.write ASLA tazelenmez.
    expect(harness.invalidate).toHaveBeenCalledWith("obsidian.write");
    expect(harness.invalidate).not.toHaveBeenCalledWith("note.write", "link.write");
    // Donen deger Vault kaydidir (DB `id` degil, `forkos_id`).
    expect(result.id).toBe("vault-1");
    expect(result.vault?.open_uri).toContain("obsidian://");
  });

  it("note: verilen baslik Vault govdesinin ilk satiri olur, ayri alan olarak gitmez", async () => {
    harness.apiPost.mockResolvedValueOnce({ forkos_id: "vault-2", open_uri: "obsidian://open" });
    await capture({ kind: "note", text: "Gövde", note: { title: "Başlık" } });
    expect(harness.apiPost).toHaveBeenCalledWith("/obsidian/capture", { body: "Başlık\n\nGövde" });
  });

  it("hicbir tur /notes ucuna dokunmaz (uc kaldirildi)", async () => {
    harness.apiPost.mockResolvedValue({ id: "x" });
    await capture({ kind: "note", text: "Not" });
    await capture({ kind: "link", text: "Makale", url: "https://example.com/a" });
    await capture({ kind: "flashcard", text: "Soru", flashcard: { deck_id: "d1", front: "Soru", back: "Cevap" } });
    expect(harness.apiPost.mock.calls.some(([path]) => String(path).includes("notes"))).toBe(false);
  });

  it("flashcard: deste ucuna gider ve flashcard.write tazelenir", async () => {
    harness.apiPost.mockResolvedValue({ id: "c1" });
    const result = await capture({
      kind: "flashcard",
      text: "Soru",
      flashcard: { deck_id: "d1", front: "Soru", back: "Cevap" },
    });
    expect(harness.apiPost).toHaveBeenCalledWith("/flashcard/decks/d1/cards", { front: "Soru", back: "Cevap" });
    expect(harness.invalidate).toHaveBeenCalledWith("flashcard.write");
    expect(result).toEqual({ kind: "flashcard", id: "c1" });
  });

  it("link: /capture'a url + koleksiyon gider, bookmark.write tazelenir", async () => {
    harness.apiPost.mockResolvedValue({ id: "b1" });
    await capture({ kind: "link", text: "Makale", url: "https://example.com/a", link: { collection: "learning" } });
    expect(harness.apiPost).toHaveBeenCalledWith("/capture", {
      url: "https://example.com/a",
      title: "Makale",
      collection: "learning",
      source: "capture",
      tags: [],
    });
    expect(harness.invalidate).toHaveBeenCalledWith("bookmark.write");
  });

  it("son kullanilan tur localStorage'da hatirlanir", () => {
    writeCaptureKindPreference("note");
    expect(readCaptureKindPreference()).toBe("note");
    writeCaptureKindPreference("link");
    expect(readCaptureKindPreference()).toBe("link");
    localStorage.removeItem("forkos.captureKind");
    expect(readCaptureKindPreference()).toBe("task");
  });

  it("eski lifeos.* anahtarindan tek seferlik goc eder", () => {
    localStorage.setItem("lifeos.captureKind", "note");
    expect(readCaptureKindPreference()).toBe("note");
    // Goc kopyalanir: sonraki okuma yeni anahtardan gelir.
    expect(localStorage.getItem("forkos.captureKind")).toBe("note");
  });
});
