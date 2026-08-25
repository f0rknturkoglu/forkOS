// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { MediaItem } from "@/core/types";
import {
  MEDIA_PROGRESS_REFRESH_KEYS,
  MediaProgressActions,
  consumptionBody,
} from "./MediaProgressActions";

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

function renderActions(online = true) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MediaProgressActions item={item} online={online} onChanged={() => undefined} />
    </QueryClientProvider>,
  );
}

describe("append-only media progress", () => {
  let calls: FetchCall[];
  let responder: () => Response | Promise<Response>;

  beforeEach(() => {
    calls = [];
    responder = () => new Response(JSON.stringify({ id: "consumption-1" }), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    });
    let uuid = 0;
    vi.spyOn(globalThis.crypto, "randomUUID").mockImplementation(
      () => `00000000-0000-4000-8000-${String(++uuid).padStart(12, "0")}` as `${string}-${string}-${string}-${string}-${string}`,
    );
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({
        body: init?.body ? JSON.parse(String(init.body)) : {},
        method: init?.method ?? "GET",
        path: new URL(String(input), "http://localhost").pathname,
      });
      return responder();
    }));
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("creates a fresh UUID for every quick, set, and finish body", () => {
    const bodies = [
      consumptionBody("quick", item),
      consumptionBody("set", item, 5),
      consumptionBody("finish", item),
    ];

    expect(bodies.map((body) => body.action)).toEqual(["quick", "set", "finish"]);
    expect(bodies[0]).toMatchObject({ amount: 1, measure: "episode" });
    expect(bodies[1]).toMatchObject({ progress_after: 5, measure: "episode" });
    expect(bodies[2]).toMatchObject({ measure: "episode" });
    expect(new Set(bodies.map((body) => body.client_uuid)).size).toBe(3);
  });

  it("invalidates every media and cross-module read model after a command", () => {
    expect(MEDIA_PROGRESS_REFRESH_KEYS).toEqual([
      "media",
      "media-detail",
      "media-stats",
      "media-dashboard",
      "today-agenda",
      "activity",
    ]);
  });

  it("posts progress commands without patching progress or completed status", async () => {
    const user = userEvent.setup();
    renderActions();

    await user.click(screen.getByRole("button", { name: "Sonraki bölüm" }));
    await user.click(screen.getByRole("button", { name: "İlerlemeyi ayarla" }));
    const progress = screen.getByRole("spinbutton", { name: "İlerleme değeri" });
    await user.clear(progress);
    await user.type(progress, "5");
    await user.click(screen.getByRole("button", { name: "İlerlemeyi kaydet" }));
    await user.click(screen.getByRole("button", { name: "Tamamlandı olarak işaretle" }));

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

  it("disables every progress write while offline", () => {
    renderActions(false);

    expect((screen.getByRole("button", { name: "Sonraki bölüm" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "İlerlemeyi ayarla" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Tamamlandı olarak işaretle" }) as HTMLButtonElement).disabled).toBe(true);
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
    responder = () => new Promise<Response>((resolve) => { settle = resolve; });
    renderActions();

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

    settle(new Response("progress rejected", { status: 500 }));
    expect((await screen.findByRole("alert")).textContent).toContain("progress rejected");
    expect(progress.value).toBe("5");

    responder = () => new Response(JSON.stringify({ id: "consumption-2" }), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    });
    await user.click(submit);
    await waitFor(() => expect(calls).toHaveLength(2));
  });
});
