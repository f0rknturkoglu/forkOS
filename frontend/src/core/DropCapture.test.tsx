// @vitest-environment jsdom
/**
 * Bırakma akışının sözleşmesi (Polish 2 §57/§58/§59).
 *
 * Kural: bir drop sonrası verilen toast aksiyonu KIRIK hedef göstermez.
 * Gelen kutusu için kanonik yüzey `/inbox` rotasıdır; belge standalone yüzeyi
 * emekliye ayrıldığı için dosya drop'u emekli sayfaya yönlendirmez, yüklenen
 * dosyanın kendisini açar.
 */
import { act, cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type * as UiModule from "@/core/ui";
import { findRouteMatch } from "@/app/router";
import "@/modules/inbox"; // kanonik hedef rotasi kayitli olsun
import { allRoutes } from "@/core/registry";
import { DropCapture } from "./DropCapture";

// jsdom 30 + Node 26 localStorage getter sorunu (CaptureDialog.test ile ayni):
// registry modul tercihlerini okurken localStorage'a dokunur.
vi.hoisted(() => {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => {
        store.set(key, value);
      },
      removeItem: (key: string) => {
        store.delete(key);
      },
      clear: () => store.clear(),
    },
  });
});

const harness = vi.hoisted(() => ({
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  toastPush: vi.fn(),
  openCapture: vi.fn(),
}));

vi.mock("@/core/api", () => ({ api: { post: harness.apiPost } }));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/CaptureDialog", () => ({ openCapture: harness.openCapture }));
vi.mock("@/core/ui", async (orig) => {
  const actual = await orig<typeof UiModule>();
  return { ...actual, useToast: () => ({ push: harness.toastPush }) };
});

type ToastOptions = { tone?: string; action?: { label: string; run: () => void } };

/** jsdom'da DataTransfer yok: birakilan icerigi tasiyan sahte olay kurulur. */
function dropEvent(payload: { files?: File[]; text?: string }) {
  const dataTransfer = {
    files: payload.files ?? [],
    types: payload.files?.length ? ["Files"] : ["text/plain"],
    getData: (type: string) => (type === "text/plain" ? (payload.text ?? "") : ""),
    dropEffect: "none",
  };
  const event = new Event("drop", { bubbles: true, cancelable: true });
  Object.defineProperty(event, "dataTransfer", { value: dataTransfer });
  return event;
}

function lastToast(): [string, ToastOptions] {
  const call = harness.toastPush.mock.calls.at(-1);
  return [call?.[0] as string, (call?.[1] ?? {}) as ToastOptions];
}

describe("DropCapture", () => {
  beforeEach(() => {
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.toastPush.mockReset();
    harness.openCapture.mockReset();
    window.location.hash = "";
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("bağlantı bırakma: gelen kutusuna yazar, 'aç' aksiyonu kanonik /inbox rotasına gider", async () => {
    harness.apiPost.mockResolvedValue({ duplicate: false });
    render(<DropCapture />);

    act(() => {
      window.dispatchEvent(dropEvent({ text: "Şunu oku: https://example.com/yazi" }));
    });
    await waitFor(() => expect(harness.toastPush).toHaveBeenCalled());

    const [message, options] = lastToast();
    expect(message).toBe("Gelen kutusuna eklendi");
    expect(options.tone).toBe("ok");
    expect(harness.apiPost).toHaveBeenCalledWith(
      "/capture",
      expect.objectContaining({ url: "https://example.com/yazi", collection: "inbox", source: "drop" }),
    );
    expect(harness.invalidate).toHaveBeenCalledWith("bookmark.write");

    act(() => options.action?.run());
    // Eski hedef `/today?triage=inbox` kayitli bir rota degildi: NotFound.
    expect(location.hash).toBe("#/inbox");
    expect(findRouteMatch(allRoutes(), "/inbox")).toBeDefined();
  });

  it("dosya bırakma: emekli belge sayfasına yönlendiren aksiyon üretmez, dosyayı açar", async () => {
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    // Gerçek /documents/upload yanıtı: yerel dosyanın açılabilir adresi.
    harness.apiPost.mockResolvedValue({ title: "rapor.pdf", web_view_link: "/api/documents/doc-1/file" });
    render(<DropCapture />);

    act(() => {
      window.dispatchEvent(dropEvent({ files: [new File(["x"], "rapor.pdf", { type: "application/pdf" })] }));
    });
    await waitFor(() => expect(harness.toastPush).toHaveBeenCalled());

    const [message, options] = lastToast();
    expect(message).toBe('"rapor.pdf" kaydedildi.');
    expect(options.tone).toBe("ok");
    expect(harness.apiPost).toHaveBeenCalledWith("/documents/upload", expect.any(FormData));
    expect(harness.invalidate).toHaveBeenCalledWith("document.write");

    const before = location.hash;
    act(() => options.action?.run());
    expect(location.hash).toBe(before); // rota degismez: "belgelere git" vaadi yok
    expect(open).toHaveBeenCalledWith("/api/documents/doc-1/file", "_blank", "noreferrer");
  });

  it("dosya bırakma: yükleme açılabilir adres döndürmezse toast aksiyonsuz kalır", async () => {
    harness.apiPost.mockResolvedValue({ title: "adsiz.pdf" });
    render(<DropCapture />);

    act(() => {
      window.dispatchEvent(dropEvent({ files: [new File(["x"], "adsiz.pdf")] }));
    });
    await waitFor(() => expect(harness.toastPush).toHaveBeenCalled());

    const [, options] = lastToast();
    expect(options.action).toBeUndefined();
  });
});
