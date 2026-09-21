// @vitest-environment jsdom
/**
 * Ağ hatalarının ürün diline çevrilmesi (Polish 1 §23/§37).
 *
 * Kural: taşıma katmanı hatası (fetch reddi, timeout, proxy HTML'i) kullanıcıya
 * ham gösterilmez; sunucunun HTTP durum kodlu JSON mesajı KORUNUR.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { API_TIMEOUT_MESSAGE, API_UNAVAILABLE_MESSAGE, ApiError, OfflineWriteError, api } from "./api";

const fetchMock = vi.fn();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
});

afterEach(() => vi.unstubAllGlobals());

describe("api ağ hataları", () => {
  it("N1: HTTP 500 sunucu mesajını korur", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: "medya kütüphanesi okunamadı" }, 500));

    await expect(api.get("/media")).rejects.toThrow("medya kütüphanesi okunamadı");
    const error = await api.get("/media").catch((thrown: unknown) => thrown);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(500);
  });

  it("N2: fetch reddi teknik 'Failed to fetch' yerine ürün mesajı verir", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    const error = await api.get("/media").catch((thrown: unknown) => thrown);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(0);
    expect((error as ApiError).message).toBe(API_UNAVAILABLE_MESSAGE);
    expect((error as ApiError).message).not.toContain("Failed to fetch");
  });

  it("N3: AbortError zaman aşımı mesajına çevrilir", async () => {
    fetchMock.mockRejectedValue(new DOMException("The operation was aborted.", "AbortError"));

    const error = await api.get("/media").catch((thrown: unknown) => thrown);
    expect((error as ApiError).message).toBe(API_TIMEOUT_MESSAGE);
  });

  it("proxy HTML hata sayfası kullanıcıya HTML olarak gösterilmez", async () => {
    fetchMock.mockResolvedValue(
      new Response("<html><head><title>502 Bad Gateway</title></head></html>", {
        status: 502,
        statusText: "Bad Gateway",
      }),
    );

    const error = await api.get("/media").catch((thrown: unknown) => thrown);
    expect((error as ApiError).status).toBe(502);
    expect((error as ApiError).message).toBe("502 Bad Gateway");
    expect((error as ApiError).message).not.toContain("<html");
    // Ham gövde programatik kullanım için saklanır.
    expect((error as ApiError).rawBody).toContain("<title>502");
  });

  it("düz metin sunucu mesajı korunur", async () => {
    fetchMock.mockResolvedValue(new Response("Not Found", { status: 404, statusText: "Not Found" }));

    const error = await api.get("/yok").catch((thrown: unknown) => thrown);
    expect((error as ApiError).message).toBe("Not Found");
  });

  it("N4: çevrimdışı yazma davranışı değişmedi", async () => {
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: false });

    await expect(api.post("/todos", { title: "x" })).rejects.toBeInstanceOf(OfflineWriteError);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("başarılı GET gövdeyi döndürür", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }));
    await expect(api.get("/health")).resolves.toEqual({ ok: true });
  });
});
