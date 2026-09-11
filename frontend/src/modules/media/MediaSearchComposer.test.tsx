// @vitest-environment jsdom

/**
 * Katalog arama govdesi sozlesmesi: debounce'lu saglayici aramasi, kapsam
 * sekmelerinin `kind` suzgeci, satir ici ekleme panosu ve 409 cakismasinda
 * mevcut kayda baglanti. Gercek ag yok; `fetch` kaydedici bir stub'dur.
 */

import { QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Mock } from "vitest";
import { queryClient } from "@/core/queryClient";
import { MediaSearchComposer, providerCreateBody } from "./MediaSearchComposer";

const libraryItem = {
  id: "media-existing",
  title: "Dune",
  kind: "movie",
  status: "planned",
  progress: 0,
  total: 1,
  score: null,
  notes: null,
  started_at: null,
  finished_at: null,
  meta: {},
  summary: null,
  release_date: null,
  progress_measure: "item",
  review: null,
  favorite: false,
  owned: false,
  ownership: {},
  monitored: false,
  provider: "tmdb",
  provider_id: "99",
  provider_ids: { tmdb: "99" },
  cover_url: null,
  cover_path: null,
  backdrop_url: null,
  backdrop_path: null,
  last_synced_at: null,
  created_at: null,
  updated_at: null,
  archived_at: null,
};

const catalogHit = {
  kind: "movie",
  provider: "tmdb",
  provider_id: "movie:99",
  title: "Dune",
  subtitle: "2021 filmi",
  summary: "Arrakis çölünde geçen uyarlama.",
  total: 1,
  progress_measure: "item",
  cover: null,
  backdrop: null,
  cover_url: "https://image.tmdb.org/t/p/w300/dune.jpg",
  backdrop_url: null,
  year: 2021,
  provider_ids: { tmdb: "99" },
  meta: { tmdb_type: "movie" },
  metadata: { ignored: true },
};

const showHit = { ...catalogHit, kind: "show", title: "Dune: Prophecy", provider_id: "tv:99" };
const addedItem = { ...libraryItem, id: "media-dune", status: "in_progress" };

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

function page(items: unknown[]): unknown {
  return { items, total: items.length, next_cursor: null };
}

function catalogPage(results: unknown[], warnings: unknown[] = []): unknown {
  return { results, warnings, cached: false };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

describe("MediaSearchComposer", () => {
  let calls: { path: string; method: string; body: unknown }[];
  let responder: (path: string, method: string) => Response | Promise<Response>;
  let onAdded: Mock;

  async function search(term: string) {
    fireEvent.change(screen.getByRole("searchbox", { name: "Katalogda ara" }), { target: { value: term } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    await flush();
  }

  /** Sabit (fake) zamanlayici altinda bekleyen promise'leri bosaltir. */
  async function flush() {
    for (let round = 0; round < 3; round += 1) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
    }
  }

  function renderComposer({ online = true, initialKind }: { online?: boolean; initialKind?: string } = {}) {
    return render(
      <QueryClientProvider client={queryClient()}>
        <MediaSearchComposer online={online} initialKind={initialKind} onAdded={onAdded} />
      </QueryClientProvider>,
    );
  }

  beforeEach(() => {
    vi.useFakeTimers();
    queryClient().clear();
    queryClient().setDefaultOptions({ queries: { retry: false, staleTime: 0 } });
    calls = [];
    onAdded = vi.fn();
    responder = (path, method) => {
      if (path === "/api/media?q=dune&limit=8") return json(page([libraryItem]));
      if (path === "/api/media/search/global?q=dune&limit=8") return json(catalogPage([catalogHit]));
      if (path === "/api/media?q=foundation&limit=8") return json(page([]));
      if (path === "/api/media/search/global?q=foundation&limit=8")
        return json(catalogPage([{ ...catalogHit, title: "Foundation" }]));
      if (path === "/api/media/collections") {
        return json([{ id: "col-1", title: "Bilim Kurgu", position: 0, item_count: 2, covers: [] }]);
      }
      if (path === "/api/media" && method === "POST") return json(addedItem, 201);
      if (path.startsWith("/api/media/collections/") && method === "POST") return new Response(null, { status: 204 });
      return json({}, 404);
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = new URL(String(input), "http://localhost");
        const path = url.pathname + url.search;
        const method = init?.method ?? "GET";
        const body = init?.body ? JSON.parse(String(init.body)) : undefined;
        calls.push({ path, method, body });
        return responder(path, method);
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("yazmadan istek atmaz ve en az iki karakter ister", async () => {
    renderComposer();

    expect(screen.getByText("Aramak için en az 2 karakter yaz.")).toBeTruthy();
    await search("d");
    expect(calls).toEqual([]);

    await search("dune");
    expect(calls.some(({ path }) => path === "/api/media?q=dune&limit=8")).toBe(true);
  });

  it("kütüphane eşleşmelerini ve katalog sonuçlarını birlikte gösterir", async () => {
    const { container } = renderComposer();
    await search("dune");

    expect(screen.getByRole("heading", { level: 2, name: "Kütüphanende" })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 2, name: "Katalog sonuçları" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Dune detayını aç" }).getAttribute("href")).toBe("#/media/media-existing");

    // Uzak kapak dogrudan cekilmez; backend onbelleginden servis edilir.
    expect(container.querySelector("ul img")?.getAttribute("src")).toBe(
      "/api/media/artwork/proxy?url=https%3A%2F%2Fimage.tmdb.org%2Ft%2Fp%2Fw300%2Fdune.jpg",
    );
    expect(within(screen.getByRole("region", { name: "Katalog sonuçları" })).getAllByText("Film")).toHaveLength(1);
    expect(screen.getAllByText("TMDB").length).toBeGreaterThan(0);
    expect(screen.getByText("2021")).toBeTruthy();
    expect(screen.getByText("Arrakis çölünde geçen uyarlama.").className).toContain("line-clamp-2");
    expect(screen.getByRole("button", { name: "Dune kaydını ekle" })).toBeTruthy();
  });

  it("kapsam seçimi kind parametresi gönderir ve tür başına sonuçları birleştirir", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    responder = (path) => {
      if (path === "/api/media?q=dune&limit=8") return json(page([]));
      if (path === "/api/media/search/global?q=dune&kind=movie&limit=8")
        return json(catalogPage([catalogHit, catalogHit]));
      if (path === "/api/media/search/global?q=dune&kind=show&limit=8") return json(catalogPage([showHit]));
      return json({}, 404);
    };
    renderComposer();
    fireEvent.click(screen.getByRole("tab", { name: "Film/dizi" }));
    await search("dune");

    const catalogPaths = calls
      .filter(({ path }) => path.startsWith("/api/media/search/global"))
      .map(({ path }) => path);
    expect(catalogPaths).toEqual([
      "/api/media/search/global?q=dune&kind=movie&limit=8",
      "/api/media/search/global?q=dune&kind=show&limit=8",
    ]);
    // Ayni (provider, provider_id, kind) uc kez gelse de tek satir cizilir.
    expect(screen.getAllByRole("heading", { level: 3 }).map((node) => node.textContent)).toEqual([
      "Dune",
      "Dune: Prophecy",
    ]);
    expect(consoleError.mock.calls.some(([message]) => String(message).includes("same key"))).toBe(false);
    consoleError.mockRestore();
  });

  it("initialKind gelen türü ilgili kapsam sekmesine çevirir", async () => {
    responder = (path) => {
      if (path === "/api/media?q=dune&limit=8") return json(page([]));
      if (path === "/api/media/search/global?q=dune&kind=game&limit=8")
        return json(catalogPage([{ ...catalogHit, kind: "game", title: "Dune II" }]));
      return json({}, 404);
    };
    renderComposer({ initialKind: "game" });
    expect(screen.getByRole("tab", { name: "Oyun", selected: true })).toBeTruthy();

    await search("dune");
    expect(calls.some(({ path }) => path === "/api/media/search/global?q=dune&kind=game&limit=8")).toBe(true);
    expect(screen.getByRole("heading", { level: 3, name: "Dune II" })).toBeTruthy();
  });

  it("satır içi panodan tür duyarlı durum, koleksiyon ve işaretleri gönderir", async () => {
    const invalidate = vi.spyOn(queryClient(), "invalidateQueries");
    renderComposer();
    await search("dune");

    fireEvent.click(screen.getByRole("button", { name: "Dune kaydını ekle" }));
    expect(screen.getByRole("button", { name: "Dune kaydını ekle" }).getAttribute("aria-expanded")).toBe("true");
    const status = screen.getByLabelText("Başlangıç durumu");
    expect(Array.from(status.querySelectorAll("option")).map((option) => option.textContent)).toEqual([
      "İzlenecek",
      "İzleniyor",
    ]);

    fireEvent.change(status, { target: { value: "in_progress" } });
    await flush();
    fireEvent.change(screen.getByLabelText("Koleksiyon"), { target: { value: "col-1" } });
    fireEvent.click(screen.getByRole("checkbox", { name: "Sahiplik" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Yeni yayınları takip et" }));
    fireEvent.click(screen.getByRole("button", { name: "Dune kaydını kütüphaneye ekle" }));
    await flush();

    expect(calls.find(({ path, method }) => path === "/api/media" && method === "POST")?.body).toEqual({
      source: "provider",
      title: "Dune",
      kind: "movie",
      provider: "tmdb",
      provider_id: "movie:99",
      provider_ids: { tmdb: "99" },
      summary: "Arrakis çölünde geçen uyarlama.",
      total: 1,
      progress_measure: "item",
      cover_url: "https://image.tmdb.org/t/p/w300/dune.jpg",
      backdrop_url: null,
      meta: { tmdb_type: "movie" },
      status: "in_progress",
      favorite: false,
      owned: true,
      monitored: true,
    });
    expect(
      calls.some(({ path, method }) => path === "/api/media/collections/col-1/items/media-dune" && method === "POST"),
    ).toBe(true);
    expect(onAdded).toHaveBeenCalledWith(addedItem);
    expect(invalidate.mock.calls.map(([filters]) => filters?.queryKey)).toContainEqual(["media"]);
    // Ekleme sonrasi pano kapanir.
    expect(screen.queryByLabelText("Koleksiyon")).toBeNull();
    invalidate.mockRestore();
  });

  it("409 çakışmasında mevcut kaydın detayına bağlantı verir", async () => {
    responder = (path, method) => {
      if (path === "/api/media?q=dune&limit=8") return json(page([]));
      if (path === "/api/media/search/global?q=dune&limit=8") return json(catalogPage([catalogHit]));
      if (path === "/api/media?q=Dune&limit=10") return json(page([libraryItem]));
      if (path === "/api/media" && method === "POST")
        return json({ detail: "Bu provider kaydi kutuphanede zaten var" }, 409);
      return json({}, 404);
    };
    renderComposer();
    await search("dune");
    fireEvent.click(screen.getByRole("button", { name: "Dune kaydını ekle" }));
    fireEvent.click(screen.getByRole("button", { name: "Dune kaydını kütüphaneye ekle" }));
    await flush();

    expect(screen.getByRole("status").textContent).toContain("Kütüphanende var");
    expect(screen.getByRole("link", { name: "Kütüphanede aç" }).getAttribute("href")).toBe("#/media/media-existing");
  });

  it("geciken 409 yanıtını yeni aramanın altında göstermez", async () => {
    const pending = deferred<Response>();
    responder = (path, method) => {
      if (path === "/api/media?q=dune&limit=8") return json(page([]));
      if (path === "/api/media/search/global?q=dune&limit=8") return json(catalogPage([catalogHit]));
      if (path === "/api/media?q=foundation&limit=8") return json(page([]));
      if (path === "/api/media/search/global?q=foundation&limit=8")
        return json(catalogPage([{ ...catalogHit, title: "Foundation" }]));
      if (path === "/api/media" && method === "POST") return pending.promise;
      return json({}, 404);
    };
    renderComposer();
    await search("dune");
    fireEvent.click(screen.getByRole("button", { name: "Dune kaydını ekle" }));
    fireEvent.click(screen.getByRole("button", { name: "Dune kaydını kütüphaneye ekle" }));
    await search("foundation");
    pending.resolve(json({ detail: "Bu provider kaydi kutuphanede zaten var" }, 409));
    await flush();

    expect(screen.queryByRole("link", { name: "Kütüphanede aç" })).toBeNull();
    expect(screen.getByRole("heading", { level: 3, name: "Foundation" })).toBeTruthy();
  });

  it("409 dışı ekleme hatasını duyurur", async () => {
    responder = (path, method) => {
      if (path === "/api/media?q=dune&limit=8") return json(page([]));
      if (path === "/api/media/search/global?q=dune&limit=8") return json(catalogPage([catalogHit]));
      if (path === "/api/media" && method === "POST") return json({ detail: "yazma kapalı" }, 500);
      return json({}, 404);
    };
    renderComposer();
    await search("dune");
    fireEvent.click(screen.getByRole("button", { name: "Dune kaydını ekle" }));
    fireEvent.click(screen.getByRole("button", { name: "Dune kaydını kütüphaneye ekle" }));
    await flush();

    expect(screen.getByRole("alert").textContent).toContain("Eklenemedi");
  });

  it("sağlayıcı uyarılarını insan diliyle gösterir, sonuçları korur", async () => {
    responder = (path) => {
      if (path === "/api/media?q=dune&limit=8") return json(page([]));
      if (path === "/api/media/search/global?q=dune&limit=8")
        return json(
          catalogPage([catalogHit], [{ provider: "tmdb", kind: "movie", message: "TMDB anahtarı tanımlı değil" }]),
        );
      return json({}, 404);
    };
    renderComposer();
    await search("dune");

    expect(screen.getByRole("status").textContent).toContain("TMDB anahtarı tanımlı değil");
    expect(screen.getByRole("link", { name: "Sağlayıcı anahtarlarını aç" }).getAttribute("href")).toBe(
      "#/settings?section=media-links",
    );
    expect(screen.getByRole("heading", { level: 3, name: "Dune" })).toBeTruthy();
  });

  it("sonuç yoksa boş durumu yazar", async () => {
    responder = (path) => {
      if (path === "/api/media?q=dune&limit=8") return json(page([]));
      if (path === "/api/media/search/global?q=dune&limit=8") return json(catalogPage([]));
      return json({}, 404);
    };
    renderComposer();
    await search("dune");

    expect(screen.getByText("Sonuç bulunamadı.")).toBeTruthy();
    expect(screen.getByText("Kütüphanende eşleşme yok.")).toBeTruthy();
  });

  it("kütüphane düşse de katalog sonuçlarını korur", async () => {
    responder = (path) => {
      if (path === "/api/media?q=dune&limit=8") return json({ detail: "kütüphane kapalı" }, 500);
      if (path === "/api/media/search/global?q=dune&limit=8") return json(catalogPage([catalogHit]));
      return json({}, 404);
    };
    renderComposer();
    await search("dune");

    expect(screen.getByRole("alert").textContent).toContain("Kütüphane");
    expect(screen.getByRole("heading", { level: 3, name: "Dune" })).toBeTruthy();
  });

  it("katalog düşse de kütüphane sonuçlarını korur", async () => {
    responder = (path) => {
      if (path === "/api/media?q=dune&limit=8") return json(page([libraryItem]));
      if (path === "/api/media/search/global?q=dune&limit=8") return json({ detail: "katalog kapalı" }, 500);
      return json({}, 404);
    };
    renderComposer();
    await search("dune");

    expect(screen.getByRole("alert").textContent).toContain("Katalog");
    expect(screen.getByRole("link", { name: "Dune detayını aç" })).toBeTruthy();
  });

  it("çevrimdışıyken ekleme yapılamaz", async () => {
    renderComposer({ online: false });
    await search("dune");

    expect((screen.getByRole("button", { name: "Dune kaydını ekle" }) as HTMLButtonElement).disabled).toBe(true);
    expect(calls.every(({ method }) => method === "GET")).toBe(true);
  });
});

describe("providerCreateBody", () => {
  it("sağlayıcı sonucunu kanonik medya gövdesine çevirir", () => {
    expect(providerCreateBody(catalogHit)).toEqual({
      source: "provider",
      title: "Dune",
      kind: "movie",
      provider: "tmdb",
      provider_id: "movie:99",
      provider_ids: { tmdb: "99" },
      summary: "Arrakis çölünde geçen uyarlama.",
      total: 1,
      progress_measure: "item",
      cover_url: "https://image.tmdb.org/t/p/w300/dune.jpg",
      backdrop_url: null,
      meta: { tmdb_type: "movie" },
      status: "planned",
      favorite: false,
      owned: false,
      monitored: false,
    });
  });
});
