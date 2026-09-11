// @vitest-environment jsdom
/**
 * Pomodoro seansi -> medya tuketimi koprusu.
 *
 * Kilitlenen davranis: idempotency anahtari seans id'sinin KENDISI olmali
 * (client_uuid uuid tipindedir, onek kabul etmez) ve varsayilan aktarim
 * ilerlemeyi ARTIRMAMALI (`action="session"`).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type { PomodoroSession } from "@/core/types";
import { ToastProvider } from "@/core/ui";
import { MediaSessionTransfer } from "./MediaSessionTransfer";

const session: PomodoroSession = {
  id: "3f1b7d1e-2c5a-4c6e-9a1f-8a2b3c4d5e6f",
  started_at: "2026-09-11T10:00:00.000Z",
  ended_at: "2026-09-11T10:25:00.000Z",
  planned_min: 25,
  actual_min: 25,
  kind: "focus",
  context_entity_id: "11111111-2222-4333-8444-555555555555",
  context_title: "Berserk 1",
  context_type: "media_item",
  topic: null,
  interrupted: false,
  paused_at: null,
  paused_s: 0,
};

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

describe("MediaSessionTransfer", () => {
  let calls: { method: string; path: string; body: unknown }[];

  beforeEach(() => {
    calls = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = new URL(String(input), "http://localhost");
        const path = url.pathname + url.search;
        const method = init?.method ?? "GET";
        calls.push({ method, path, body: init?.body ? JSON.parse(String(init.body)) : null });
        if (path.startsWith("/api/media/11111111-2222-4333-8444-555555555555") && method === "GET") {
          return json({ item: { progress_measure: "page", kind: "book", title: "Berserk 1" } });
        }
        if (path.endsWith("/consumptions") && method === "POST") return json({ id: "c1" }, 201);
        return json({ detail: "unexpected" }, 404);
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  function renderDialog(value: PomodoroSession | null = session, onClose = vi.fn()) {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <MediaSessionTransfer session={value} onClose={onClose} />
        </ToastProvider>
      </QueryClientProvider>,
    );
    return { onClose };
  }

  it("does not render while there is no finished session", () => {
    renderDialog(null);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("logs duration only by default: action=session, no amount, session id as client_uuid", async () => {
    const { onClose } = renderDialog();
    expect(await screen.findByText(/İlerlemeyi de \+1 sayfa artır/)).toBeTruthy();

    screen.getByRole("button", { name: "Süreyi tüketime aktar" }).click();

    await vi.waitFor(() => expect(calls.some((call) => call.method === "POST")).toBe(true));
    const post = calls.find((call) => call.method === "POST");
    expect(post?.path).toBe("/api/media/11111111-2222-4333-8444-555555555555/consumptions");
    expect(post?.body).toMatchObject({
      client_uuid: session.id,
      action: "session",
      duration_min: 25,
      measure: "page",
      meta: { pomodoro_session_id: session.id },
    });
    expect((post?.body as { amount?: number }).amount).toBeUndefined();
    await vi.waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it("adds one unit of progress when the user opts in", async () => {
    renderDialog();
    const toggle = await screen.findByRole("checkbox", { name: /İlerlemeyi de \+1 sayfa artır/ });
    (toggle as HTMLInputElement).click();

    screen.getByRole("button", { name: "Süreyi ve +1 sayfa kaydet" }).click();

    await vi.waitFor(() => expect(calls.some((call) => call.method === "POST")).toBe(true));
    const post = calls.find((call) => call.method === "POST");
    expect(post?.body).toMatchObject({ action: "quick", amount: 1, duration_min: 25, measure: "page" });
  });

  it("keeps the session in the pomodoro history when the user declines", () => {
    const { onClose } = renderDialog();
    screen.getByRole("button", { name: "Yalnızca odak süresini kaydet" }).click();
    expect(calls.some((call) => call.method === "POST")).toBe(false);
    expect(onClose).toHaveBeenCalled();
  });
});
