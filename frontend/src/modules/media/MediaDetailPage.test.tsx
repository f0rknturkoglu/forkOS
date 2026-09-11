// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { allRoutes } from "@/core/registry";
import "./index";
import { MediaDetailPage } from "./MediaDetailPage";

const item = {
  archived_at: null,
  backdrop_path: null,
  backdrop_url: "https://images.example.test/dune-backdrop.jpg",
  cover_path: null,
  cover_url: "https://images.example.test/dune.jpg",
  created_at: "2026-08-20T10:00:00Z",
  favorite: false,
  finished_at: null,
  id: "media-1",
  kind: "show",
  last_synced_at: "2026-08-23T10:00:00Z",
  meta: { original_title: "Dune: Prophecy" },
  monitored: true,
  notes: "İkinci sezon",
  owned: true,
  ownership: { format: "Dijital", platform: "HBO Max" },
  progress: 3,
  progress_measure: "episode",
  provider: "tmdb",
  provider_id: "tv:42",
  provider_ids: { tmdb: "42" },
  release_date: "2026-01-01",
  review: "İlk sezonu sevdim.",
  score: 8,
  started_at: "2026-08-01T10:00:00Z",
  status: "in_progress",
  summary: "Bir bilim kurgu dizisi.",
  title: "Dune: Prophecy",
  total: 8,
  updated_at: "2026-08-23T10:00:00Z",
};

function unit(id: string, title: string, number: number, extra: Record<string, unknown> = {}) {
  return {
    id,
    media_id: "media-1",
    parent_id: null,
    title,
    unit_type: "episode",
    number,
    duration_min: 51,
    release_at: "2026-02-01T10:00:00Z",
    progress_total: 1,
    progress_measure: "episode",
    provider: "tmdb",
    provider_id: id,
    provider_ids: {},
    cover_url: null,
    cover_path: null,
    meta: {},
    children: [],
    created_at: "2026-02-01T10:00:00Z",
    updated_at: "2026-02-01T10:00:00Z",
    ...extra,
  };
}

const episodes = [unit("episode-1", "Birinci bölüm", 1), unit("episode-2", "İkinci bölüm", 2)];
const season = unit("season-1", "1. Sezon", 1, {
  unit_type: "season",
  duration_min: null,
  progress_total: null,
  children: episodes,
});

const consumption = {
  id: "consumption-1",
  media_id: "media-1",
  cycle_id: "cycle-1",
  unit_id: "episode-2",
  client_uuid: "11111111-1111-4111-8111-111111111111",
  action: "complete_unit",
  measure: "episode",
  amount: 1,
  progress_after: 3,
  occurred_at: "2026-08-22T10:00:00Z",
  duration_min: 51,
  note: null,
  meta: {},
  created_at: "2026-08-22T10:00:00Z",
};

const firstPage = {
  items: [
    {
      ...consumption,
      id: "consumption-2",
      action: "quick",
      measure: "page",
      amount: 12,
      progress_after: 132,
      duration_min: null,
      note: "sabah okuması",
      unit_id: null,
    },
  ],
  total: 3,
  next_cursor: "cursor-2",
};

const secondPage = {
  items: [
    {
      ...consumption,
      id: "consumption-3",
      action: "set",
      measure: "page",
      amount: -2,
      progress_after: 130,
      duration_min: null,
      note: null,
      unit_id: null,
    },
  ],
  total: 3,
  next_cursor: null,
};

const collection = {
  id: "collection-1",
  title: "Favoriler",
  position: 0,
  color: null,
  description: null,
  item_count: 1,
  covers: [],
  created_at: "2026-08-01T10:00:00Z",
  updated_at: "2026-08-01T10:00:00Z",
};

const detail = {
  item,
  units: [season],
  cycles: [],
  consumptions: [consumption],
  collections: [collection],
  consumption_count: 3,
  sync: { status: "ok", last_run_at: "2026-09-01T10:00:00Z", last_error: null, items_found: 4 },
};

const tmdbProvider = {
  id: "tmdb",
  kinds: ["movie", "show"],
  ready: true,
  missing_settings: [],
  last_run_at: null,
  last_status: null,
  last_error: null,
  state: "ready",
  next_run_at: null,
  capabilities: {
    search: true,
    details: true,
    units: true,
    upcoming: true,
    cache_artwork: true,
    requires_settings: [],
  },
};

type FetchCall = { body: Record<string, unknown>; method: string; path: string };

function json(value: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function defaultResponder(path: string, method: string): Response {
  if (method === "GET") {
    if (path.startsWith("/api/media/providers")) return json([tmdbProvider]);
    if (path.includes("/consumptions")) return json(firstPage);
    if (path.startsWith("/api/entities/")) return json([]);
    if (path.startsWith("/api/media/")) return json(detail);
  }
  if (path.startsWith("/api/notes")) return json({ id: "note-1" }, 201);
  if (path.startsWith("/api/todos")) return json({ id: "todo-1" }, 201);
  return json(item);
}

function renderPage(path = "#/media/media-1") {
  location.hash = path;
  fireEvent(window, new HashChangeEvent("hashchange"));
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MediaDetailPage />
    </QueryClientProvider>,
  );
}

describe("media detail page", () => {
  let calls: FetchCall[];
  let responder: (path: string, method: string) => Response | Promise<Response>;

  beforeEach(() => {
    calls = [];
    responder = defaultResponder;
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: { getItem: () => null, setItem: vi.fn(), removeItem: vi.fn() },
    });
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = new URL(String(input), "http://localhost");
        const method = init?.method ?? "GET";
        calls.push({
          body: init?.body ? JSON.parse(String(init.body)) : {},
          method,
          path: url.pathname + url.search,
        });
        return responder(url.pathname + url.search, method);
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("registers the encoded dynamic detail route after the media index", () => {
    const paths = allRoutes().filter((route) => route.path === "/media" || route.path.startsWith("/media/:"));
    expect(paths.map((route) => route.path)).toEqual(["/media", "/media/:id"]);
  });

  it("loads a readable two-column detail with progress, backdrop and source actions", async () => {
    renderPage("#/media/media%2Fone");

    expect(await screen.findByRole("heading", { name: "Dune: Prophecy" })).toBeTruthy();
    expect(calls[0].path).toBe("/api/media/media%2Fone");
    const cover = screen.getByRole("img", { name: "Dune: Prophecy kapağı" });
    expect(cover.className).toContain("w-full");
    const backdrop = document.querySelector("img[alt='']");
    expect(backdrop?.parentElement?.getAttribute("aria-hidden")).toBe("true");
    expect(screen.getByText("İzleniyor")).toBeTruthy();
    expect(screen.getByText("3 / 8 bölüm")).toBeTruthy();
    const bar = screen.getByRole("progressbar", { name: "Dune: Prophecy ilerlemesi" });
    expect(bar.getAttribute("aria-valuenow")).toBe("38");
    expect(bar.getAttribute("aria-valuemin")).toBe("0");
    expect(bar.getAttribute("aria-valuemax")).toBe("100");
    expect(screen.getByRole("button", { name: "+1 bölüm" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "İzlemeyi tamamla" })).toBeTruthy();
    expect(screen.getByText("8 / 10")).toBeTruthy();
    expect(screen.getByText("3 / 8 bölüm")).toBeTruthy();
    expect(screen.getByText("HBO Max")).toBeTruthy();
    expect(screen.getByText("Dijital")).toBeTruthy();
    expect((screen.getByRole("textbox", { name: "Notlar" }) as HTMLTextAreaElement).value).toBe("İkinci sezon");
    expect((screen.getByRole("textbox", { name: "İnceleme" }) as HTMLTextAreaElement).value).toBe("İlk sezonu sevdim.");
    expect(screen.getByRole("link", { name: /TMDB/ })).toBeTruthy();
    expect(screen.getByRole("link", { name: /IMDb/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Koleksiyona ekle" })).toBeTruthy();
  });

  it("renders no backdrop when the record has none", async () => {
    responder = (path, method) =>
      method === "GET" && path.startsWith("/api/media/media-1") && !path.includes("consumptions")
        ? json({ ...detail, item: { ...item, backdrop_url: null, backdrop_path: null } })
        : defaultResponder(path, method);
    renderPage();

    expect(await screen.findByRole("heading", { name: "Dune: Prophecy" })).toBeTruthy();
    expect(document.querySelector("img[alt='']")).toBeNull();
  });

  it("keeps one accessible rating control and patches only the score", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    // Yildiz dizisi/cip kombinasyonu YOK: tek kaydirma cubugu.
    expect(screen.getAllByRole("slider")).toHaveLength(1);
    expect(screen.queryAllByRole("radio")).toHaveLength(0);
    const slider = screen.getByRole("slider", { name: "Puan" });
    expect(slider.getAttribute("min")).toBe("1");
    expect(slider.getAttribute("max")).toBe("10");
    expect(slider.getAttribute("aria-valuetext")).toBe("8 / 10");

    fireEvent.change(slider, { target: { value: "9" } });
    expect(slider.getAttribute("aria-valuetext")).toBe("9 / 10");
    await user.click(screen.getByRole("button", { name: "Puanı kaydet" }));

    await waitFor(() => expect(calls.some((call) => call.method === "PATCH")).toBe(true));
    expect(calls.filter((call) => call.method === "PATCH")).toEqual([
      { method: "PATCH", path: "/api/media/media-1", body: { score: 9 } },
    ]);
  });

  it("clears a score with a null patch", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    await user.click(screen.getByRole("button", { name: "Puanı temizle" }));
    await waitFor(() => expect(calls.some((call) => call.method === "PATCH")).toBe(true));
    expect(calls.filter((call) => call.method === "PATCH")).toEqual([
      { method: "PATCH", path: "/api/media/media-1", body: { score: null } },
    ]);
  });

  it("patches notes and review separately and never progress or status", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    const notes = screen.getByRole("textbox", { name: "Notlar" });
    await user.clear(notes);
    await user.type(notes, "Yeni not");
    await user.click(screen.getByRole("button", { name: "Notları kaydet" }));
    await waitFor(() => expect(calls.some((call) => call.method === "PATCH")).toBe(true));

    const review = screen.getByRole("textbox", { name: "İnceleme" });
    await user.clear(review);
    await user.type(review, "Yeni inceleme");
    await user.click(screen.getByRole("button", { name: "İncelemeyi kaydet" }));
    await waitFor(() => expect(calls.filter((call) => call.method === "PATCH")).toHaveLength(2));

    expect(calls.filter((call) => call.method === "PATCH")).toEqual([
      { method: "PATCH", path: "/api/media/media-1", body: { notes: "Yeni not" } },
      { method: "PATCH", path: "/api/media/media-1", body: { review: "Yeni inceleme" } },
    ]);
    expect(calls.filter((call) => call.method === "PATCH").some(({ body }) => "progress" in body)).toBe(false);
    expect(calls.filter((call) => call.method === "PATCH").some(({ body }) => body.status === "completed")).toBe(false);
  });

  it("toggles favorite and new release tracking through single metadata patches", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    await user.click(screen.getByRole("button", { name: "Favorilere ekle" }));
    await waitFor(() => expect(calls.some((call) => call.method === "PATCH")).toBe(true));
    expect(calls.filter((call) => call.method === "PATCH")).toEqual([
      { method: "PATCH", path: "/api/media/media-1", body: { favorite: true } },
    ]);

    await user.click(screen.getByRole("checkbox", { name: "Yeni yayınları takip et" }));
    await waitFor(() => expect(calls.filter((call) => call.method === "PATCH")).toHaveLength(2));
    expect(calls.filter((call) => call.method === "PATCH")[1]).toEqual({
      method: "PATCH",
      path: "/api/media/media-1",
      body: { monitored: false },
    });
  });

  it("disables new release tracking with a visible reason when the provider cannot track releases", async () => {
    responder = (path, method) =>
      method === "GET" && path.startsWith("/api/media/providers")
        ? json([{ ...tmdbProvider, capabilities: { ...tmdbProvider.capabilities, upcoming: false } }])
        : defaultResponder(path, method);
    renderPage();

    await screen.findByRole("heading", { name: "Dune: Prophecy" });
    const checkbox = screen.getByRole("checkbox", { name: "Yeni yayınları takip et" }) as HTMLInputElement;
    expect(checkbox.disabled).toBe(true);
    expect(screen.getByText("TMDB yeni yayın bilgisi sağlamıyor.")).toBeTruthy();
  });

  it("refreshes metadata through a single sync call and reports the run result inline", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    expect(screen.getByText(/4 kayıt bulundu/)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Metadata'yı yenile" }));
    await waitFor(() => expect(calls.some((call) => call.method === "POST")).toBe(true));
    const posts = calls.filter((call) => call.method === "POST");
    expect(posts).toHaveLength(1);
    expect(posts[0].path).toBe("/api/media/sync?item_id=media-1");
  });

  it("blocks duplicate sync triggers and explains why tracking must be on first", async () => {
    let posts = 0;
    let settle!: (response: Response) => void;
    responder = (path, method) => {
      if (method === "POST" && path.startsWith("/api/media/sync")) {
        posts += 1;
        return new Promise<Response>((resolve) => {
          settle = resolve;
        });
      }
      return defaultResponder(path, method);
    };
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    const button = screen.getByRole("button", { name: "Metadata'yı yenile" }) as HTMLButtonElement;
    fireEvent.click(button);
    await waitFor(() => expect(posts).toBe(1));
    expect(button.disabled).toBe(true);
    fireEvent.click(button);
    expect(posts).toBe(1);
    settle(json({ scope: "media", status: "queued", source_ids: [], total_sources: 1 }));
    await waitFor(() => expect(button.disabled).toBe(false));
  });

  it("requires new release tracking before metadata can be refreshed", async () => {
    responder = (path, method) =>
      method === "GET" && path.startsWith("/api/media/media-1") && !path.includes("consumptions")
        ? json({ ...detail, item: { ...item, monitored: false } })
        : defaultResponder(path, method);
    renderPage();

    await screen.findByRole("heading", { name: "Dune: Prophecy" });
    expect((screen.getByRole("button", { name: "Metadata'yı yenile" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Önce yeni yayın takibini aç")).toBeTruthy();
  });

  it("surfaces a failed sync run with the recorded error", async () => {
    responder = (path, method) =>
      method === "GET" && path.startsWith("/api/media/media-1") && !path.includes("consumptions")
        ? json({
            ...detail,
            sync: {
              status: "error",
              last_run_at: "2026-09-01T10:00:00Z",
              last_error: "TMDB anahtarı geçersiz",
              items_found: null,
            },
          })
        : defaultResponder(path, method);
    renderPage();

    await screen.findByRole("heading", { name: "Dune: Prophecy" });
    expect((await screen.findByRole("alert")).textContent).toContain("TMDB anahtarı geçersiz");
    expect(screen.getByRole("status").textContent).toContain("Son yenileme hatalı");
  });

  it("pages through consumption history and labels every row in Turkish", async () => {
    const user = userEvent.setup();
    responder = (path, method) => {
      if (method === "GET" && path.includes("/consumptions")) {
        return path.includes("cursor-2") ? json(secondPage) : json(firstPage);
      }
      return defaultResponder(path, method);
    };
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    expect(screen.getByText("3 kayıt")).toBeTruthy();
    expect(screen.getByText("Hızlı ilerleme")).toBeTruthy();
    expect(screen.getByText("12 sayfa")).toBeTruthy();
    expect(screen.getByText("→ 132 sayfa")).toBeTruthy();
    expect(screen.getByText("sabah okuması")).toBeTruthy();
    expect(calls.some((call) => call.path === "/api/media/media-1/consumptions?limit=20")).toBe(true);

    await user.click(screen.getByRole("button", { name: "Daha fazla yükle" }));
    await waitFor(() =>
      expect(calls.some((call) => call.path === "/api/media/media-1/consumptions?limit=20&cursor=cursor-2")).toBe(true),
    );
    expect(screen.getByText("→ 130 sayfa")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Daha fazla yükle" })).toBeNull();
  });

  it("shows nested units behind an accessible disclosure and keeps completion labels", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    const toggle = screen.getByRole("button", { name: "1. Sezon alt kayıtlarını göster" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("button", { name: "Birinci bölümü tamamla" })).toBeNull();

    await user.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByRole("button", { name: "İkinci bölümün tamamlamasını geri al" })).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Birinci bölümü tamamla" }));
    await waitFor(() => expect(calls.some((call) => call.method === "POST")).toBe(true));
    const posts = calls.filter((call) => call.method === "POST");
    expect(posts[0].path).toBe("/api/media/media-1/consumptions");
    expect(posts[0].body).toMatchObject({ action: "complete_unit", unit_id: "episode-1", measure: "episode" });
    expect(Boolean(posts[0].body.client_uuid)).toBe(true);
  });

  it("builds the same unit tree from a flat parent_id list", async () => {
    const flat = [
      unit("season-1", "1. Sezon", 1, { unit_type: "season", children: undefined }),
      unit("episode-1", "Birinci bölüm", 1, { parent_id: "season-1" }),
      unit("episode-2", "İkinci bölüm", 2, { children: undefined }),
    ];
    responder = (path, method) =>
      method === "GET" && path.startsWith("/api/media/media-1") && !path.includes("consumptions")
        ? json({ ...detail, units: flat, consumptions: [] })
        : defaultResponder(path, method);
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    expect(screen.queryByRole("button", { name: "Birinci bölümü tamamla" })).toBeNull();
    // parent_id'si olmayan kayit duz listede kalir -- sahte hiyerarsi kurulmaz.
    expect(screen.getByRole("button", { name: "İkinci bölümü tamamla" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "1. Sezon alt kayıtlarını göster" }));
    expect(screen.getByRole("button", { name: "Birinci bölümü tamamla" })).toBeTruthy();
  });

  it("speaks the record's kind in actions, progress and session labels", async () => {
    responder = (path, method) =>
      method === "GET" && path.startsWith("/api/media/media-1") && !path.includes("consumptions")
        ? json({
            ...detail,
            units: [],
            item: {
              ...item,
              kind: "book",
              provider: "openlibrary",
              progress: 120,
              total: 300,
              progress_measure: "page",
            },
          })
        : defaultResponder(path, method);
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    expect(screen.getByText("120 / 300 sayfa")).toBeTruthy();
    expect(screen.getByRole("button", { name: "+1 sayfa" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Okumayı tamamla" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Okumaya başla" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Okuma seansı başlat" })).toBeTruthy();
  });

  it("starts a pomodoro session bound to the record", async () => {
    const user = userEvent.setup();
    const opened = vi.fn();
    window.addEventListener("forkos:pomodoro-open", opened);
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    await user.click(screen.getByRole("button", { name: "İzleme seansı başlat" }));
    expect(opened).toHaveBeenCalledTimes(1);
    expect((opened.mock.calls[0][0] as CustomEvent).detail).toEqual({
      context: "media-1",
      topic: "Dune: Prophecy",
    });
    window.removeEventListener("forkos:pomodoro-open", opened);
  });

  it("creates a note bound to the record and opens it in the notes module", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    await user.click(screen.getByRole("button", { name: "Not oluştur" }));
    const dialog = await screen.findByRole("dialog", { name: "Not oluştur" });
    expect(dialog).toBeTruthy();
    await user.type(screen.getByRole("textbox", { name: "Not başlığı" }), "Dune notları");
    await user.type(screen.getByRole("textbox", { name: "İlk satır" }), "İlk izlenim");
    await user.click(screen.getByRole("button", { name: "Notu oluştur ve aç" }));

    await waitFor(() => expect(calls.some((call) => call.path === "/api/notes" && call.method === "POST")).toBe(true));
    expect(calls.find((call) => call.path === "/api/notes")?.body).toEqual({
      body: "Dune notları\n\nİlk izlenim",
      relate_to: "media-1",
    });
    await waitFor(() => expect(location.hash).toContain("/notes?focus=note-1"));
  });

  it("creates a todo from the shared intent layer and links it to the record", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    await user.click(screen.getByRole("button", { name: "Görev oluştur" }));
    expect(await screen.findByRole("dialog", { name: "Görev oluştur" })).toBeTruthy();
    const title = screen.getByRole("textbox", { name: "Görev başlığı" }) as HTMLInputElement;
    expect(title.value).toBe("Dune: Prophecy — ");
    await user.type(title, "4. bölümü izle");
    await user.click(screen.getByRole("button", { name: "Görevi oluştur" }));

    await waitFor(() => expect(calls.some((call) => call.path === "/api/links")).toBe(true));
    expect(calls.find((call) => call.path === "/api/todos")?.body).toEqual({
      title: "Dune: Prophecy — 4. bölümü izle",
      priority: 2,
      description: "Dizi · Dune: Prophecy",
    });
    expect(calls.find((call) => call.path === "/api/links")?.body).toEqual({
      from_id: "todo-1",
      to_id: "media-1",
      relation: "related",
    });
  });

  it("opens the shared highlight dialog from the record", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    await user.click(screen.getByRole("button", { name: "Alıntı ekle" }));
    expect(await screen.findByRole("dialog", { name: "Alıntı ekle" })).toBeTruthy();
  });

  it("keeps every detail write disabled offline while still loading the detail", async () => {
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: false });
    renderPage();

    expect(await screen.findByRole("heading", { name: "Dune: Prophecy" })).toBeTruthy();
    for (const name of [
      "+1 bölüm",
      "İzlemeyi tamamla",
      "İlerlemeyi ayarla",
      "İzlemeye başla",
      "İzleme seansı başlat",
      "Puanı kaydet",
      "Puanı temizle",
      "Notları kaydet",
      "İncelemeyi kaydet",
      "Metadata'yı yenile",
      "Not oluştur",
      "Alıntı ekle",
      "Görev oluştur",
      "Koleksiyona ekle",
    ]) {
      expect((screen.getByRole("button", { name }) as HTMLButtonElement).disabled).toBe(true);
    }
    expect((screen.getByRole("button", { name: "Favorilere ekle" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("checkbox", { name: "Yeni yayınları takip et" }) as HTMLInputElement).disabled).toBe(true);
    expect(calls.some((call) => call.method === "GET")).toBe(true);
    expect(calls.some((call) => call.method !== "GET")).toBe(false);
  });

  it("restores the previous document title after leaving the detail", async () => {
    document.title = "forkOS";
    const view = renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });
    await waitFor(() => expect(document.title).toBe("Dune: Prophecy — forkOS"));

    view.unmount();
    expect(document.title).toBe("forkOS");
  });

  it("retries a terminal detail GET failure", async () => {
    let gets = 0;
    responder = (path, method) => {
      if (method !== "GET") return json(item);
      if (path.includes("/consumptions")) return json(firstPage);
      if (path.startsWith("/api/media/providers")) return json([tmdbProvider]);
      if (path.startsWith("/api/entities/")) return json([]);
      gets += 1;
      return gets === 1 ? new Response("detail unavailable", { status: 500 }) : json(detail);
    };
    const user = userEvent.setup();
    renderPage();

    expect((await screen.findByRole("alert")).textContent).toContain("detail unavailable");
    await user.click(screen.getByRole("button", { name: "Yeniden dene" }));
    expect(await screen.findByRole("heading", { name: "Dune: Prophecy" })).toBeTruthy();
    expect(gets).toBe(2);
  });

  it("blocks duplicate pending metadata patches and preserves the text for retry", async () => {
    let patchCount = 0;
    let rejectPatch!: (response: Response) => void;
    responder = (path, method) => {
      if (method === "GET") return defaultResponder(path, method);
      patchCount += 1;
      if (patchCount === 1)
        return new Promise<Response>((resolve) => {
          rejectPatch = resolve;
        });
      return json(item);
    };
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    const notes = screen.getByRole("textbox", { name: "Notlar" }) as HTMLTextAreaElement;
    await user.clear(notes);
    await user.type(notes, "Retry notu");
    const submit = screen.getByRole("button", { name: "Notları kaydet" }) as HTMLButtonElement;
    fireEvent.click(submit);
    await waitFor(() => expect(patchCount).toBe(1));
    expect(submit.disabled).toBe(true);
    fireEvent.click(submit);
    expect(patchCount).toBe(1);

    rejectPatch(new Response("metadata rejected", { status: 500 }));
    expect((await screen.findByRole("alert")).textContent).toContain("metadata rejected");
    expect(notes.value).toBe("Retry notu");

    await user.click(submit);
    await waitFor(() => expect(patchCount).toBe(2));
  });

  it("pauses an active open cycle through a status patch", async () => {
    const user = userEvent.setup();
    responder = (path, method) => {
      if (method === "GET" && path.startsWith("/api/media/media-1") && !path.includes("consumptions")) {
        return json({
          ...detail,
          cycles: [
            {
              id: "cycle-1",
              media_id: "media-1",
              ordinal: 2,
              status: "active",
              started_at: "2026-09-01T10:00:00Z",
              completed_at: null,
            },
          ],
        });
      }
      return defaultResponder(path, method);
    };
    renderPage();

    expect(await screen.findByRole("heading", { name: "Dune: Prophecy" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Duraklat" }));
    await waitFor(() => expect(calls.some((call) => call.method === "PATCH")).toBe(true));
    const patches = calls.filter((call) => call.method === "PATCH");
    expect(patches).toHaveLength(1);
    expect(patches[0]).toEqual({ method: "PATCH", path: "/api/media/media-1", body: { status: "paused" } });
  });

  it("resumes a paused cycle through a status patch", async () => {
    const user = userEvent.setup();
    responder = (path, method) => {
      if (method === "GET" && path.startsWith("/api/media/media-1") && !path.includes("consumptions")) {
        return json({
          ...detail,
          item: { ...item, status: "paused" },
          cycles: [
            {
              id: "cycle-1",
              media_id: "media-1",
              ordinal: 2,
              status: "paused",
              started_at: "2026-09-01T10:00:00Z",
              completed_at: null,
            },
          ],
        });
      }
      return defaultResponder(path, method);
    };
    renderPage();

    expect(await screen.findByRole("heading", { name: "Dune: Prophecy" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "İzlemeye devam et" }));
    await waitFor(() => expect(calls.some((call) => call.method === "PATCH")).toBe(true));
    const patches = calls.filter((call) => call.method === "PATCH");
    expect(patches).toHaveLength(1);
    expect(patches[0]).toEqual({ method: "PATCH", path: "/api/media/media-1", body: { status: "in_progress" } });
  });

  it("starts watching planned media only when no open cycle exists", async () => {
    const user = userEvent.setup();
    responder = (path, method) => {
      if (method === "GET" && path.startsWith("/api/media/media-1") && !path.includes("consumptions")) {
        return json({ ...detail, item: { ...item, status: "planned", progress: 0 } });
      }
      return defaultResponder(path, method);
    };
    renderPage();

    expect(await screen.findByRole("heading", { name: "Dune: Prophecy" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Duraklat" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "İzlemeye başla" }));
    await waitFor(() => expect(calls.some((call) => call.method === "POST")).toBe(true));
    const posts = calls.filter((call) => call.method === "POST");
    expect(posts).toHaveLength(1);
    expect(posts[0].path).toBe("/api/media/media-1/cycles");
  });
});
