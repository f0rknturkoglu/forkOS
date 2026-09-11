import { queryClient } from "@/core/queryClient";
// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { MediaItem } from "@/core/types";
import { AFTER } from "@/core/invalidation";
import { ToastProvider } from "@/core/ui";
import { MediaProgressActions, actionLabel, consumptionBody, kindLanguage, measureLabel } from "./MediaProgressActions";

const item = {
  id: "media/one",
  title: "Dune: Prophecy",
  kind: "show",
  status: "in_progress",
  progress: 3,
  total: 8,
  progress_measure: "episode",
} as MediaItem;

type FetchCall = { body: Record<string, unknown>; method: string; path: string };

/** `invalidateAfter` tek arguman gecirir; spy'in tipi genis oldugu icin daraltma burada yapilir. */
type InvalidatedFilters = { queryKey: string[] };

function renderActions(online = true, mediaItem: MediaItem = item, { withToast = false } = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const invalidate = vi.spyOn(queryClient(), "invalidateQueries").mockResolvedValue(undefined);
  const view = render(
    <QueryClientProvider client={client}>
      {withToast ? (
        <ToastProvider>
          <MediaProgressActions item={mediaItem} online={online} onChanged={() => undefined} />
        </ToastProvider>
      ) : (
        <MediaProgressActions item={mediaItem} online={online} onChanged={() => undefined} />
      )}
    </QueryClientProvider>,
  );
  return { ...view, invalidate };
}

describe("append-only media progress", () => {
  let calls: FetchCall[];
  let responder: () => Response | Promise<Response>;

  beforeEach(() => {
    calls = [];
    responder = () =>
      new Response(JSON.stringify({ id: "consumption-1" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      });
    let uuid = 0;
    vi.spyOn(globalThis.crypto, "randomUUID").mockImplementation(
      () =>
        `00000000-0000-4000-8000-${String(++uuid).padStart(12, "0")}` as `${string}-${string}-${string}-${string}-${string}`,
    );
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        calls.push({
          body: init?.body ? JSON.parse(String(init.body)) : {},
          method: init?.method ?? "GET",
          path: new URL(String(input), "http://localhost").pathname,
        });
        return responder();
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("creates a fresh UUID for every quick, set, and finish body", () => {
    const bodies = [consumptionBody("quick", item), consumptionBody("set", item, 5), consumptionBody("finish", item)];

    expect(bodies.map((body) => body.action)).toEqual(["quick", "set", "finish"]);
    expect(bodies[0]).toMatchObject({ amount: 1, measure: "episode" });
    expect(bodies[1]).toMatchObject({ progress_after: 5, measure: "episode" });
    expect(bodies[2]).toMatchObject({ measure: "episode" });
    expect(new Set(bodies.map((body) => body.client_uuid)).size).toBe(3);
  });

  it("invalidates every media and cross-module read model after a command", () => {
    expect(AFTER["media.write"]).toEqual([
      "media",
      "media-detail",
      "media-stats",
      "media-dashboard",
      "media-collections",
      "today-agenda",
      "activity",
      "statistics",
      "deadlines",
      "graph",
      "related",
    ]);
  });

  it("speaks the record's kind in verbs, progress and session language", () => {
    expect(kindLanguage("show")).toMatchObject({
      verb: "İzle",
      start: "İzlemeye başla",
      resume: "İzlemeye devam et",
      finish: "İzlemeyi tamamla",
      session: "İzleme seansı başlat",
    });
    expect(kindLanguage("movie").verb).toBe("İzle");
    expect(kindLanguage("anime").verb).toBe("İzle");
    expect(kindLanguage("book")).toMatchObject({
      verb: "Oku",
      finish: "Okumayı tamamla",
      session: "Okuma seansı başlat",
    });
    expect(kindLanguage("manga").verb).toBe("Oku");
    expect(kindLanguage("audiobook").verb).toBe("Dinle");
    expect(kindLanguage("podcast").verb).toBe("Dinle");
    expect(kindLanguage("music").session).toBe("Dinleme seansı başlat");
    expect(kindLanguage("game")).toMatchObject({
      verb: "Oyna",
      finish: "Oyunu tamamla",
      session: "Oyun seansı başlat",
    });
    // Legacy/bilinmeyen tur cokmez, notr dile duser.
    expect(kindLanguage(undefined).verb).toBe("İncele");
    expect(kindLanguage("legacy-unknown").restart).toBe("Sıfırdan başla");
  });

  it("labels consumption actions and measures in Turkish", () => {
    expect(actionLabel("quick")).toBe("Hızlı ilerleme");
    expect(actionLabel("set")).toBe("Düzeltme");
    expect(actionLabel("finish")).toBe("Tamamlama");
    expect(actionLabel("complete_unit")).toBe("Bölüm tamamlandı");
    expect(actionLabel("uncomplete_unit")).toBe("Geri alındı");
    expect(actionLabel("session")).toBe("Seans");
    expect(actionLabel(null)).toBe("Kayıt");
    expect(measureLabel("page")).toBe("sayfa");
    expect(measureLabel("episode")).toBe("bölüm");
    expect(measureLabel("chapter")).toBe("bölüm");
    expect(measureLabel("track")).toBe("parça");
    expect(measureLabel("minute")).toBe("dakika");
    expect(measureLabel("hour")).toBe("saat");
    expect(measureLabel("item")).toBe("kayıt");
    expect(measureLabel(null)).toBe("kayıt");
  });

  it("renders kind-sensitive progress buttons", () => {
    const book = { ...item, kind: "book", progress_measure: "page" } as MediaItem;
    const view = renderActions(true, book);

    expect(screen.getByRole("button", { name: "+1 sayfa" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Okumayı tamamla" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "+1 bölüm" })).toBeNull();
    view.unmount();

    renderActions(true, { ...item, kind: "game" } as MediaItem);
    expect(screen.getByRole("button", { name: "Oyunu tamamla" })).toBeTruthy();
  });

  it("groups quick/finish under saving and the correction form under fixing", async () => {
    const user = userEvent.setup();
    renderActions();

    expect(screen.getByRole("group", { name: "İlerleme kaydet" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "İlerlemeyi düzelt" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "İlerlemeyi ayarla" }));
    expect(screen.getByRole("form", { name: "Kesin ilerleme" })).toBeTruthy();
  });

  it("posts progress commands without patching progress or completed status", async () => {
    const user = userEvent.setup();
    renderActions();

    await user.click(screen.getByRole("button", { name: "+1 bölüm" }));
    await user.click(screen.getByRole("button", { name: "İlerlemeyi ayarla" }));
    const progress = screen.getByRole("spinbutton", { name: "İlerleme değeri" });
    await user.clear(progress);
    await user.type(progress, "5");
    await user.click(screen.getByRole("button", { name: "İlerlemeyi kaydet" }));
    await user.click(screen.getByRole("button", { name: "İzlemeyi tamamla" }));

    await waitFor(() => expect(calls).toHaveLength(3));
    const posts = calls.filter((call) => call.method === "POST");
    const patches = calls.filter((call) => call.method === "PATCH");
    expect(posts.map((post) => post.path)).toEqual([
      "/api/media/media%2Fone/consumptions",
      "/api/media/media%2Fone/consumptions",
      "/api/media/media%2Fone/consumptions",
    ]);
    expect(posts.map((post) => post.body.action)).toEqual(["quick", "set", "finish"]);
    expect(posts[0].body).toMatchObject({ amount: 1, measure: "episode" });
    expect(posts[1].body).toMatchObject({ progress_after: 5, measure: "episode" });
    expect(new Set(posts.map((post) => post.body.client_uuid)).size).toBe(3);
    expect(patches.some(({ body }) => "progress" in body || body.status === "completed")).toBe(false);
  });

  it("offers an undo that appends a compensating set consumption", async () => {
    const user = userEvent.setup();
    const { invalidate } = renderActions(true, item, { withToast: true });

    await user.click(screen.getByRole("button", { name: "+1 bölüm" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].body).toMatchObject({ action: "quick", amount: 1 });

    // Toast aksiyonu: ayni yazimi geri alir, mevcut event'i GUNCELLEMEZ.
    await user.click(await screen.findByRole("button", { name: "Geri al" }));
    await waitFor(() => expect(calls).toHaveLength(2));
    expect(calls[1]).toEqual({
      body: {
        action: "set",
        client_uuid: "00000000-0000-4000-8000-000000000002",
        measure: "episode",
        note: "geri alındı",
        progress_after: 3,
      },
      method: "POST",
      path: "/api/media/media%2Fone/consumptions",
    });
    const invalidatedKeys = invalidate.mock.calls.map((call) => (call[0] as InvalidatedFilters).queryKey);
    expect(invalidatedKeys.filter((key) => key[0] === "media")).toHaveLength(2);
  });

  it("disables every progress write while offline", () => {
    renderActions(false);

    expect((screen.getByRole("button", { name: "+1 bölüm" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "İlerlemeyi ayarla" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "İzlemeyi tamamla" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("requires an explicit retryable cycle start after completion and refreshes every read model", async () => {
    const completed = { ...item, status: "completed", progress: 8 } as MediaItem;
    let attempts = 0;
    responder = () => {
      attempts += 1;
      return attempts === 1
        ? new Response("cycle rejected", { status: 500 })
        : new Response(JSON.stringify({ id: "cycle-2" }), {
            status: 201,
            headers: { "Content-Type": "application/json" },
          });
    };
    const user = userEvent.setup();
    const { invalidate } = renderActions(true, completed);

    expect(screen.queryByRole("button", { name: "+1 bölüm" })).toBeNull();
    expect(screen.queryByRole("button", { name: "İlerlemeyi ayarla" })).toBeNull();
    expect(screen.queryByRole("button", { name: "İzlemeyi tamamla" })).toBeNull();
    const start = screen.getByRole("button", { name: "Sıfırdan başla" });

    await user.click(start);
    expect((await screen.findByRole("alert")).textContent).toContain("cycle rejected");
    expect(calls).toEqual([{ body: {}, method: "POST", path: "/api/media/media%2Fone/cycles" }]);

    await user.click(start);
    await waitFor(() => expect(calls).toHaveLength(2));
    const invalidatedKeys = invalidate.mock.calls.map((call) => (call[0] as InvalidatedFilters).queryKey);
    expect(invalidatedKeys).toEqual(AFTER["media.write"].map((key) => [key]));
  });

  it("keeps the explicit new-cycle write disabled offline", () => {
    const completed = { ...item, status: "completed", progress: 8 } as MediaItem;
    renderActions(false, completed);

    expect((screen.getByRole("button", { name: "Sıfırdan başla" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByRole("button", { name: "+1 bölüm" })).toBeNull();
  });

  it("treats dropped media as terminal and starts its next cycle only explicitly", async () => {
    const dropped = { ...item, status: "dropped" } as MediaItem;
    const user = userEvent.setup();
    renderActions(true, dropped);

    expect(screen.queryByRole("button", { name: "+1 bölüm" })).toBeNull();
    expect(screen.queryByRole("button", { name: "İlerlemeyi ayarla" })).toBeNull();
    expect(screen.queryByRole("button", { name: "İzlemeyi tamamla" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Sıfırdan başla" }));

    await waitFor(() => expect(calls).toEqual([{ body: {}, method: "POST", path: "/api/media/media%2Fone/cycles" }]));
  });

  it("lays out the exact progress form without narrow-screen overflow", async () => {
    const user = userEvent.setup();
    renderActions();
    await user.click(screen.getByRole("button", { name: "İlerlemeyi ayarla" }));

    const form = screen.getByRole("form", { name: "Kesin ilerleme" });
    expect(form.className).toContain("grid");
    expect(form.className).toContain("min-w-0");
    expect(screen.getByRole("spinbutton", { name: "İlerleme değeri" }).className).toContain("w-full");
    const submit = screen.getByRole("button", { name: "İlerlemeyi kaydet" });
    expect(submit.className).toContain("w-full");
    expect(submit.className).toContain("sm:w-auto");
  });

  it("blocks duplicate pending POSTs and preserves set input after rejection for retry", async () => {
    const user = userEvent.setup();
    let settle!: (response: Response) => void;
    responder = () =>
      new Promise<Response>((resolve) => {
        settle = resolve;
      });
    const { invalidate } = renderActions();

    await user.click(screen.getByRole("button", { name: "İlerlemeyi ayarla" }));
    const progress = screen.getByRole("spinbutton", { name: "İlerleme değeri" }) as HTMLInputElement;
    await user.clear(progress);
    await user.type(progress, "5");
    const submit = screen.getByRole("button", { name: "İlerlemeyi kaydet" }) as HTMLButtonElement;
    fireEvent.click(submit);
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(submit.disabled).toBe(true);
    fireEvent.click(submit);
    expect(calls).toHaveLength(1);

    const beforeFailure = invalidate.mock.calls.length;
    settle(new Response("progress rejected", { status: 500 }));
    expect((await screen.findByRole("alert")).textContent).toContain("progress rejected");
    expect(progress.value).toBe("5");
    // Basarisiz yazimdan sonra detay/liste sorgulari tazelenir (tek geri alma katmani).
    expect(invalidate.mock.calls.length).toBeGreaterThan(beforeFailure);

    responder = () =>
      new Response(JSON.stringify({ id: "consumption-2" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      });
    await user.click(submit);
    await waitFor(() => expect(calls).toHaveLength(2));
  });
});
