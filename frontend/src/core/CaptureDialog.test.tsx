// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type * as ObsidianModule from "@/core/obsidian";
import { CaptureDialog, openCapture } from "./CaptureDialog";
import { todayKey, tomorrowKey } from "@/lib/date";

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

type MutationOptions = {
  mutationKey?: readonly unknown[];
  mutationFn?: (variables: never) => Promise<unknown> | unknown;
  onSuccess?: (result: unknown) => void;
  onError?: () => void;
};

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  toastPush: vi.fn(),
  openUri: vi.fn(),
  mutations: [] as MutationOptions[],
  pending: false,
}));

vi.mock("@/core/api", () => ({ api: { get: harness.apiGet, post: harness.apiPost } }));
vi.mock("@/lib/hooks", () => ({
  useOnline: () => true,
  useDebounced: (value: string) => value,
}));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/core/queryClient", () => ({ queryClient: vi.fn() }));
vi.mock("@/core/obsidian", async (orig) => {
  const actual = await orig<typeof ObsidianModule>();
  return { ...actual, openObsidianUri: (uri: string) => harness.openUri(uri) };
});
vi.mock("@/core/ui", async (orig) => {
  const actual = await orig<typeof import("@/core/ui")>();
  return { ...actual, useToast: () => ({ push: harness.toastPush }) };
});
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn((options: MutationOptions) => {
    harness.mutations.push(options);
    return {
      isPending: harness.pending,
      // Gercek async davranis: mutationFn await edilir, onSuccess/onError
      // ona gore calisir. Reject edilen promise asla unhandled kalmaz.
      mutate: async (variables: never) => {
        try {
          const result = await options.mutationFn?.(variables);
          options.onSuccess?.(result);
        } catch {
          options.onError?.();
        }
      },
    };
  }),
  useQuery: vi.fn((options: { queryKey: readonly unknown[]; queryFn: () => unknown }) => {
    const key = String(options.queryKey[0]);
    if (key === "search") {
      return {
        data: [{ id: "opp-1", type: "opportunity", title: "Fırsat A", created_at: "", updated_at: "" }],
      };
    }
    return { data: [] };
  }),
}));

describe("CaptureDialog (Faz 22/29)", () => {
  beforeEach(() => {
    localStorage.clear();
    harness.apiGet.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.toastPush.mockReset();
    harness.openUri.mockReset();
    harness.mutations.length = 0;
    harness.pending = false;
  });
  afterEach(() => cleanup());

  function openAs(prefill: { text?: string; kind?: "task" | "note" | "link" }) {
    render(<CaptureDialog />);
    act(() => openCapture(prefill));
  }

  it("acilinca tur sekmeleri gorunur; secilen tur gonderilmeden once belli", () => {
    openAs({ text: "Test metni" });
    expect(screen.getByRole("dialog", { name: "Hızlı yakala" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Görev/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Not/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Bağlantı/ })).toBeTruthy();
    expect(screen.getByLabelText("Görev başlığı")).toBeTruthy();
  });

  it("URL prefill baglanti turunu ONERIR ama kullanici turu degistirebilir", async () => {
    openAs({ text: "https://example.com/yazi" });
    expect(screen.getByLabelText("Bağlantı adresi")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Bağlantı adresi"), {
      target: { value: "https://example.com/yazi" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Yakala" }));
    await waitFor(() => expect(harness.apiPost).toHaveBeenCalled());
    const [path, body] = harness.apiPost.mock.calls[0];
    expect(path).toBe("/capture");
    expect(body.url).toBe("https://example.com/yazi");
    expect(body.source).toBe("capture");

    // Kullanici turu degistirebilir: Not sekmesine gec.
    fireEvent.click(screen.getByRole("button", { name: /Not/ }));
    expect(screen.getByLabelText("Not içeriği")).toBeTruthy();
  });

  it("baglanti icin baslik tek basina yetmez; gecerli HTTP(S) adresi zorunludur", () => {
    openAs({ kind: "link" });
    fireEvent.change(screen.getByLabelText("Bağlantı başlığı"), { target: { value: "Sadece başlık" } });
    expect((screen.getByRole("button", { name: "Yakala" }) as HTMLButtonElement).disabled).toBe(true);

    fireEvent.change(screen.getByLabelText("Bağlantı adresi"), { target: { value: "javascript:alert(1)" } });
    expect((screen.getByRole("button", { name: "Yakala" }) as HTMLButtonElement).disabled).toBe(true);

    fireEvent.change(screen.getByLabelText("Bağlantı adresi"), { target: { value: "https://example.com" } });
    expect((screen.getByRole("button", { name: "Yakala" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("Enter tek kayit olusturur", async () => {
    openAs({ text: "Enter ile gorev" });
    const input = screen.getByLabelText("Görev başlığı");
    fireEvent.change(input, { target: { value: "Enter ile gorev" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => expect(harness.apiPost).toHaveBeenCalledTimes(1));
    expect(harness.apiPost.mock.calls[0][0]).toBe("/todos");
  });

  it("pending iken gonderim kilitlenir (ikinci kayit olusmaz)", () => {
    harness.pending = true;
    openAs({ text: "Bekleyen gorev" });
    expect((screen.getByRole("button", { name: "Yakalanıyor…" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Yakalanıyor…" }));
    expect(harness.apiPost).not.toHaveBeenCalled();
  });

  it("Escape kayit olusturmadan kapatir", () => {
    openAs({ text: "Kapatilacak" });
    // Keydown form'un icine (input) verilir; form'un onKeyDown'i yakalar.
    fireEvent.keyDown(screen.getByLabelText("Görev başlığı"), { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(harness.apiPost).not.toHaveBeenCalled();
  });

  it("tekrar + etiketler gonderilen task intent'ine ulasir", async () => {
    openAs({ text: "Rutin gorev" });
    fireEvent.click(screen.getByRole("button", { name: "her gün" }));
    const tagInput = screen.getByLabelText("Etiket");
    fireEvent.change(tagInput, { target: { value: "is" } });
    fireEvent.keyDown(tagInput, { key: "Enter" });

    fireEvent.click(screen.getByRole("button", { name: "Yakala" }));
    await waitFor(() => expect(harness.apiPost).toHaveBeenCalled());
    const [path, body] = harness.apiPost.mock.calls[0];
    expect(path).toBe("/todos");
    expect(body.recur).toBe("daily");
    expect(body.tags).toEqual(["is"]);
  });

  it("not iliskilendirme: secilen kayit relate_to olarak Vault yakalamasina gider", async () => {
    harness.apiPost.mockResolvedValue({
      forkos_id: "vault-9",
      open_uri: "obsidian://open?vault=f0rknbrain&file=00%20Inbox%2FToplanti",
    });
    openAs({ text: "Toplanti notu", kind: "note" });
    const relate = screen.getByLabelText("İlişkilendirilecek kayıt");
    fireEvent.change(relate, { target: { value: "Firsat" } });
    await screen.findByText("Fırsat A");
    fireEvent.click(screen.getByText("Fırsat A"));

    fireEvent.click(screen.getByRole("button", { name: "Yakala" }));
    await waitFor(() => expect(harness.apiPost).toHaveBeenCalled());
    const [path, body] = harness.apiPost.mock.calls[0];
    expect(path).toBe("/obsidian/capture");
    expect(body).toEqual({ body: "Toplanti notu", relate_to: "opp-1" });
    // forkOS not entity'si kaldirildi: hicbir tur /notes'a dokunmaz.
    expect(harness.apiPost.mock.calls.some(([call]) => String(call).includes("notes"))).toBe(false);
    expect(harness.invalidate).toHaveBeenCalledWith("obsidian.write");
    expect(harness.invalidate).not.toHaveBeenCalledWith("note.write", "link.write");
  });

  it("not sekmesi 'sabitle' kontrolunu kaldirir, Vault ipucunu gosterir", () => {
    openAs({ text: "Not", kind: "note" });
    expect(screen.queryByText("sabitle")).toBeNull();
    expect(screen.getByText(/Obsidian Vault'una/)).toBeTruthy();
  });

  it("not basarili olunca Vault bildirimi gonderir ve notu Obsidian'da acar", async () => {
    harness.apiPost.mockResolvedValue({
      forkos_id: "vault-9",
      open_uri: "obsidian://open?vault=f0rknbrain&file=00%20Inbox%2FNot",
    });
    openAs({ text: "Not", kind: "note" });
    fireEvent.click(screen.getByRole("button", { name: "Yakala" }));

    await waitFor(() => expect(harness.toastPush).toHaveBeenCalled());
    const [message, options] = harness.toastPush.mock.calls[0];
    expect(message).toContain("Obsidian");
    expect(options.tone).toBe("ok");
    options.action.run();
    expect(harness.openUri).toHaveBeenCalledWith("obsidian://open?vault=f0rknbrain&file=00%20Inbox%2FNot");
  });

  it("parser temiz basligi gonderir: 'yarin 14:00 disciyi ara' -> 'disciyi ara'", async () => {
    openAs({ text: "yarın 14:00 dişçiyi ara" });
    // "Metinden çözüldü" seridi gorunur (Faz 23/30).
    expect(screen.getByText(/Metinden çözüldü/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Yakala" }));
    await waitFor(() => expect(harness.apiPost).toHaveBeenCalled());
    const [, body] = harness.apiPost.mock.calls[0];
    expect(body.title).toBe("dişçiyi ara");
    expect(body.plan_day).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("metindeki acik yarin ifadesi global bugune al tercihinden once gelir", async () => {
    localStorage.setItem("todo.planToday", "1");
    openAs({ text: "yarın raporu bitir" });
    fireEvent.click(screen.getByRole("button", { name: "Yakala" }));
    await waitFor(() => expect(harness.apiPost).toHaveBeenCalled());
    const [, body] = harness.apiPost.mock.calls[0];
    expect(body.plan_day).toBe(tomorrowKey());
    expect(body.plan_day).not.toBe(todayKey());
  });

  it("parser direktifi metinden silinince parsera ait eski plan gununu temizler", async () => {
    openAs({ text: "yarın raporu bitir" });
    fireEvent.change(screen.getByLabelText("Görev başlığı"), { target: { value: "raporu bitir" } });
    fireEvent.click(screen.getByRole("button", { name: "Yakala" }));
    await waitFor(() => expect(harness.apiPost).toHaveBeenCalled());
    const [, body] = harness.apiPost.mock.calls[0];
    expect(body.plan_day).toBeUndefined();
  });

  it("unhandled rejection uretmez: hata onError'a gider, suite temiz cikar", async () => {
    harness.apiPost.mockRejectedValueOnce(new Error("offline"));
    openAs({ text: "Basarisiz gorev" });
    fireEvent.click(screen.getByRole("button", { name: "Yakala" }));
    // Mutation reject eder; dialog acik kalir ve daha sonra yeniden denenebilir.
    await waitFor(() => expect(harness.apiPost).toHaveBeenCalled());
  });
  it("traps keyboard focus and restores opener without capturing on Escape", () => {
    const opener = document.createElement("button");
    document.body.append(opener);
    opener.focus();
    openAs({ kind: "task" });
    const dialog = screen.getByRole("dialog", { name: "Hızlı yakala" });
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    screen.getByRole("button", { name: "Görev" }).focus();
    fireEvent.keyDown(document.activeElement!, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(screen.getByLabelText("Etiket"));
    fireEvent.keyDown(document.activeElement!, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(harness.apiPost).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(opener);
    opener.remove();
  });
});
