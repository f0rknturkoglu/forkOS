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

  it("note: TEK istek /notes; relate_to ayni gövdede gider (Faz 29)", async () => {
    harness.apiPost.mockResolvedValueOnce({ id: "n1" });
    await capture({ kind: "note", text: "Toplantı notu", note: { pinned: true, relate_to: "opp-1" } });
    expect(harness.apiPost).toHaveBeenCalledTimes(1);
    expect(harness.apiPost).toHaveBeenCalledWith("/notes", {
      body: "Toplantı notu",
      pinned: true,
      relate_to: "opp-1",
    });
    expect(harness.invalidate).toHaveBeenCalledWith("note.write", "link.write");
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
    localStorage.removeItem("lifeos.captureKind");
    expect(readCaptureKindPreference()).toBe("task");
  });
});
