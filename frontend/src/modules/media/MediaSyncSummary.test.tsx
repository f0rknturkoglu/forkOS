// @vitest-environment jsdom

/**
 * Kaynak ozeti sozlesmesi: durum kirilimi (`state`), "0 saglikli" gibi
 * tum-hepsi-bozuk imasi yok, tek tetik + offline kilit ve okunabilir tani.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { queryClient } from "@/core/queryClient";
import { MediaSyncSummary } from "./MediaSyncSummary";

const CAPABILITIES = {
  search: true,
  details: true,
  units: true,
  upcoming: false,
  cache_artwork: true,
  requires_settings: [],
};

const providers = [
  {
    id: "tmdb",
    kinds: ["movie", "show"],
    ready: true,
    state: "ok",
    missing_settings: [],
    last_run_at: "2026-08-25T07:30:00.000Z",
    last_status: "ok",
    last_error: null,
    last_items_found: 12,
    capabilities: CAPABILITIES,
  },
  {
    id: "anilist",
    kinds: ["anime", "manga"],
    ready: true,
    state: "ok",
    missing_settings: [],
    last_run_at: "2026-08-25T07:20:00.000Z",
    last_status: "ok",
    last_error: null,
    last_items_found: 3,
    capabilities: CAPABILITIES,
  },
  {
    id: "openlibrary",
    kinds: ["book"],
    ready: true,
    state: "empty",
    missing_settings: [],
    last_run_at: "2026-08-25T07:00:00.000Z",
    last_status: "empty",
    last_error: null,
    last_items_found: 0,
    capabilities: CAPABILITIES,
  },
  {
    id: "itunes",
    kinds: ["music", "podcast"],
    ready: true,
    state: "ok",
    missing_settings: [],
    last_run_at: "2026-08-25T06:30:00.000Z",
    last_status: "ok",
    last_error: null,
    last_items_found: 8,
    capabilities: CAPABILITIES,
  },
  {
    id: "igdb",
    kinds: ["game"],
    ready: true,
    state: "never_run",
    missing_settings: [],
    last_run_at: null,
    last_status: null,
    last_error: null,
    last_items_found: null,
    capabilities: CAPABILITIES,
  },
  {
    id: "google_books",
    kinds: ["book"],
    ready: false,
    state: "missing_settings",
    missing_settings: ["media.google_books_key"],
    last_run_at: null,
    last_status: null,
    last_error: null,
    last_items_found: null,
    capabilities: { ...CAPABILITIES, requires_settings: ["media.google_books_key"] },
  },
];

const BREAKDOWN =
  "5 kullanılabilir · 1 yapılandırılmamış · henüz çalışmadı: 1 · son tarama başarılı: 3 · son tarama boş: 1";

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

function renderSummary(online = true) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const view = render(
    <QueryClientProvider client={client}>
      <MediaSyncSummary online={online} />
    </QueryClientProvider>,
  );
  return { ...view, client };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

describe("MediaSyncSummary", () => {
  let calls: { method: string; path: string }[];
  let responder: (path: string, method: string) => Response | Promise<Response>;

  beforeEach(() => {
    vi.spyOn(Date, "now").mockReturnValue(new Date("2026-08-25T08:00:00.000Z").getTime());
    calls = [];
    responder = (path, method) => {
      if (path === "/api/media/providers") return json(providers);
      if (path === "/api/sources/sync?scope=media")
        return json({ active: null, last_completed: null, running: [], sources: [] });
      if (path === "/api/media/sync" && method === "POST") return json({ queued: 6 });
      return json({ detail: "unexpected request" }, 404);
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = new URL(String(input), "http://localhost");
        const path = url.pathname + url.search;
        const method = init?.method ?? "GET";
        calls.push({ path, method });
        return responder(path, method);
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("özet satırında durum kırılımını yazar, sağlık iması kurmaz", async () => {
    renderSummary();

    expect(await screen.findByText("6 kaynak")).toBeTruthy();
    expect(screen.getByText(BREAKDOWN)).toBeTruthy();
    expect(screen.getByText("son çekim 30 dk önce")).toBeTruthy();
    expect(screen.queryByText(/sağlıklı/)).toBeNull();
    expect(screen.queryByText(/hazır değil/)).toBeNull();
  });

  it("satır durumunu state'ten türetir ve eksik ayarı insan diliyle yazar", async () => {
    const { container } = renderSummary();
    await screen.findByText("6 kaynak");
    const details = container.querySelector("details[data-media-sync]") as HTMLDetailsElement;
    expect(details.open).toBe(false);
    fireEvent.click(screen.getByText("Kaynak ayrıntıları"));
    expect(details.open).toBe(true);

    expect(screen.getByText("TMDB")).toBeTruthy();
    expect(screen.getByText("Film · Dizi")).toBeTruthy();
    expect(within(screen.getByText("TMDB").closest("li")!).getByText("Son tarama başarılı (12 kayıt)")).toBeTruthy();
    expect(within(screen.getByText("OpenLibrary").closest("li")!).getByText("Son tarama boş")).toBeTruthy();
    expect(within(screen.getByText("IGDB").closest("li")!).getByText("Henüz çalışmadı")).toBeTruthy();
    expect(screen.getByText("Eksik yapılandırma: Google Books anahtarı")).toBeTruthy();
    expect(screen.queryByText(/media\.google_books_key/)).toBeNull();
  });

  it("taranan sağlayıcı varken elle tetiklemeyi kilitler", async () => {
    responder = (path) =>
      path === "/api/media/providers"
        ? json([{ ...providers[0], state: "running", last_status: "running" }, providers[4]])
        : json({ active: null, last_completed: null, running: [], sources: [] });
    renderSummary();
    await screen.findByText("2 kaynak");
    fireEvent.click(screen.getByText("Kaynak ayrıntıları"));

    expect(screen.getByText("Taranıyor…")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Şimdi tara" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("bekleyen taramayı çiftlemez ve tüm sorgu ailelerini tazeler", async () => {
    const pending = deferred<Response>();
    responder = (path, method) => {
      if (path === "/api/media/providers") return json(providers);
      if (path === "/api/sources/sync?scope=media")
        return json({ active: null, last_completed: null, running: [], sources: [] });
      if (path === "/api/media/sync" && method === "POST") return pending.promise;
      return json({}, 404);
    };
    renderSummary();
    const invalidate = vi.spyOn(queryClient(), "invalidateQueries");
    fireEvent.click(await screen.findByText("Kaynak ayrıntıları"));
    const sync = screen.getByRole("button", { name: "Şimdi tara" }) as HTMLButtonElement;
    fireEvent.click(sync);
    expect(await screen.findByRole("button", { name: "Şimdi tara" })).toBe(sync);
    expect(sync.disabled).toBe(true);
    fireEvent.click(sync);
    expect(calls.filter((call) => call.path === "/api/media/sync" && call.method === "POST")).toHaveLength(1);

    pending.resolve(json({ queued: 6 }));
    await act(async () => {});
    const keys = invalidate.mock.calls.map(([filters]) => filters?.queryKey);
    expect(keys).toContainEqual(["media-providers"]);
    expect(keys).toContainEqual(["source-sync"]);
    expect(keys).toContainEqual(["media"]);
    invalidate.mockRestore();
  });

  it("çevrimdışıyken tarama başlatmaz", async () => {
    renderSummary(false);
    fireEvent.click(await screen.findByText("Kaynak ayrıntıları"));

    expect((screen.getByRole("button", { name: "Şimdi tara" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("yükleme ve tetikleme hatalarını görünür kılar, yeniden dener", async () => {
    let providerGets = 0;
    responder = (path, method) => {
      if (path === "/api/media/providers") {
        providerGets += 1;
        return providerGets === 1 ? json({ detail: "sağlayıcılar kapalı" }, 500) : json(providers);
      }
      if (path === "/api/sources/sync?scope=media")
        return json({ active: null, last_completed: null, running: [], sources: [] });
      if (path === "/api/media/sync" && method === "POST") return json({ detail: "kuyruk kapalı" }, 500);
      return json({}, 404);
    };
    renderSummary();

    expect((await screen.findByRole("alert")).textContent).toContain("sağlayıcılar kapalı");
    const details = document.querySelector("details[data-media-sync]") as HTMLDetailsElement;
    expect(details.open).toBe(true);
    fireEvent.click(screen.getByText("Kaynak ayrıntıları"));
    await act(async () => {
      details.dispatchEvent(new Event("toggle"));
    });
    expect(details.open).toBe(false);
    expect(details.querySelector("svg")?.className.baseVal).not.toContain("rotate-180");

    fireEvent.click(screen.getByText("Kaynak ayrıntıları"));
    expect(details.open).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Yeniden dene" }));
    expect(await screen.findByText("6 kaynak")).toBeTruthy();

    fireEvent.click(screen.getByText("Kaynak ayrıntıları"));
    fireEvent.click(screen.getByRole("button", { name: "Şimdi tara" }));
    expect((await screen.findByRole("alert")).textContent).toContain("kuyruk kapalı");
    expect((screen.getByRole("button", { name: "Şimdi tara" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("boş panelde satır içi boş durum ve ayar kısayolu gösterir", async () => {
    responder = (path) =>
      path === "/api/media/providers"
        ? json([])
        : json({ active: null, last_completed: null, running: [], sources: [] });
    renderSummary();
    fireEvent.click(await screen.findByText("Kaynak ayrıntıları"));

    expect(await screen.findByText(/Yapılandırılmış medya sağlayıcısı yok\./)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Sağlayıcı anahtarlarını aç" }).getAttribute("href")).toBe(
      "#/settings?section=media-links",
    );
  });

  it("uzun tanı metnini kırpar, okunur bırakır", async () => {
    const longError = "Sağlayıcının ayrıntılı yanıtı: geçici ağ geçidi hatası nedeniyle katalog bağlantısı kurulamadı.";
    responder = (path) =>
      path === "/api/media/providers"
        ? json([{ ...providers[0], state: "error", last_status: "error", last_error: longError }])
        : json({ active: null, last_completed: null, running: [], sources: [] });
    renderSummary();
    await screen.findByText("1 kaynak");
    fireEvent.click(screen.getByText("Kaynak ayrıntıları"));

    const error = screen.getByText(`Son tarama hatalı: ${longError}`);
    expect(error.className).toContain("break-words");
    expect(error.className).not.toContain("truncate");
    expect(error.getAttribute("title")).toBe(`Son tarama hatalı: ${longError}`);
  });
});
