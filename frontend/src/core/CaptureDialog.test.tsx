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

type MutationOptions = { mutationKey?: readonly unknown[]; mutationFn?: (variables: never) => unknown };

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  mutations: [] as MutationOptions[],
  pending: false,
}));

vi.mock("@/core/api", () => ({ api: { get: harness.apiGet, post: harness.apiPost } }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/core/queryClient", () => ({ queryClient: vi.fn() }));
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn((options: MutationOptions) => {
    harness.mutations.push(options);
    return {
      isPending: harness.pending,
      mutate: (variables: never) => void options.mutationFn?.(variables),
    };
  }),
  useQuery: vi.fn(() => ({ data: [] })),
}));

describe("CaptureDialog (Faz 22)", () => {
  beforeEach(() => {
    localStorage.clear();
    harness.apiGet.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.mutations.length = 0;
    harness.pending = false;
  });
  afterEach(() => cleanup());

  it("acilinca tur sekmeleri gorunur; secilen tur gonderilmeden once belli", () => {
    render(<CaptureDialog />);
    act(() => openCapture({ text: "Test metni" }));
    expect(screen.getByRole("dialog", { name: "Hızlı yakala" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Görev/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Not/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Bağlantı/ })).toBeTruthy();
    expect(screen.getByLabelText("Görev başlığı")).toBeTruthy();
  });

  it("URL prefille gelirse baglanti onerilir ve /capture'a gider", async () => {
    render(<CaptureDialog />);
    act(() => openCapture({ text: "https://example.com/yazi" }));
    expect(screen.getByLabelText("Bağlantı adresi")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Bağlantı adresi"), { target: { value: "https://example.com/yazi" } });
    fireEvent.click(screen.getByRole("button", { name: "Yakala" }));
    await waitFor(() => expect(harness.apiPost).toHaveBeenCalled());
    const [path, body] = harness.apiPost.mock.calls[0];
    expect(path).toBe("/capture");
    expect(body.url).toBe("https://example.com/yazi");
    expect(body.source).toBe("capture");
  });

  it("gonderim beklerken Yakala kilitlenir (double submit yok)", () => {
    harness.pending = true;
    const { unmount } = render(<CaptureDialog />);
    act(() => openCapture({ text: "Metin" }));
    // Pending iken etiket "Yakalanıyor…" ve buton kilitli (double submit yok).
    const button = screen.getByRole("button", { name: "Yakalanıyor…" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    unmount();
    harness.pending = false;
  });
});
