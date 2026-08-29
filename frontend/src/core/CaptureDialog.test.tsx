// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CaptureDialog, openCapture } from "./CaptureDialog";

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

  it("not iliskilendirme: secilen kayit relate_to olarak TEK istekte gider", async () => {
    openAs({ text: "Toplanti notu", kind: "note" });
    const relate = screen.getByLabelText("İlişkilendirilecek kayıt");
    fireEvent.change(relate, { target: { value: "Firsat" } });
    await screen.findByText("Fırsat A");
    fireEvent.click(screen.getByText("Fırsat A"));

    fireEvent.click(screen.getByRole("button", { name: "Yakala" }));
    await waitFor(() => expect(harness.apiPost).toHaveBeenCalled());
    const [path, body] = harness.apiPost.mock.calls[0];
    expect(path).toBe("/notes");
    expect(body.relate_to).toBe("opp-1");
  });

  it("unhandled rejection uretmez: hata onError'a gider, suite temiz cikar", async () => {
    harness.apiPost.mockRejectedValueOnce(new Error("offline"));
    openAs({ text: "Basarisiz gorev" });
    fireEvent.click(screen.getByRole("button", { name: "Yakala" }));
    // Mutation reject eder; dialog acik kalir ve daha sonra yeniden denenebilir.
    await waitFor(() => expect(harness.apiPost).toHaveBeenCalled());
  });
});
