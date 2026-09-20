// @vitest-environment jsdom

/**
 * Bildirim panelindeki H6 erteleme kontrolu: yalnizca kosusu bulunan
 * (`notification_id` eslesen) `proactivity` bildirimlerinde gorunur ve
 * erteleme O kosuya gider. Gercek ag yok; `fetch` kaydedici bir stub'dur.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "./ui";
import { NotificationPanel } from "./NotificationPanel";

interface Call {
  method: string;
  path: string;
  body?: Record<string, unknown>;
}

let calls: Call[] = [];

function json(value: unknown): Response {
  return new Response(JSON.stringify(value), { status: 200, headers: { "Content-Type": "application/json" } });
}

function lastCall(method: string, path: string): Call | undefined {
  return [...calls].reverse().find((call) => call.method === method && call.path === path);
}

const NOTIFICATIONS = [
  {
    id: 42,
    kind: "proactivity",
    title: "Proje durdu",
    body: null,
    entity_id: null,
    entity_type: null,
    importance: 2,
    created_at: "2026-09-21T09:00:00+00:00",
    read_at: null,
  },
  {
    id: 43,
    kind: "proactivity.digest",
    title: "Günlük özet",
    body: null,
    entity_id: null,
    entity_type: null,
    importance: 1,
    created_at: "2026-09-21T08:00:00+00:00",
    read_at: null,
  },
  {
    id: 44,
    kind: "source",
    title: "Kaynak hatası",
    body: null,
    entity_id: null,
    entity_type: null,
    importance: 1,
    created_at: "2026-09-21T07:00:00+00:00",
    read_at: null,
  },
];

/** Yalnizca 42 numarali bildirime bagli bir kosu var; 43'un kosusu YOK. */
const RUNS = [
  {
    id: 7,
    rule_kind: "project_stalled",
    subject_type: "project",
    subject_id: "11111111-1111-1111-1111-111111111111",
    state: "delivered",
    reason_codes: ["PROJECT_STALLED"],
    why_now: "projede 16 gündür kayıtlı anlamlı aktivite yok",
    triggered_at: "2026-09-21T09:00:00+00:00",
    delivered_at: "2026-09-21T09:00:00+00:00",
    delivery_count: 1,
    snoozed_until: null,
    notification_id: 42,
    failure_code: null,
  },
];

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <NotificationPanel />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const method = (init?.method ?? "GET").toUpperCase();
      calls.push({ method, path: url.pathname, body: init?.body ? JSON.parse(String(init.body)) : undefined });

      if (url.pathname === "/api/notifications") return json(NOTIFICATIONS);
      if (url.pathname === "/api/proactivity/history") return json(RUNS);
      return json({});
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("NotificationPanel erteleme", () => {
  it("yalnız eşleşen koşusu olan H6 bildiriminde erteleme menüsü sunar", async () => {
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: /^Bildirimler/ }));
    expect(await screen.findByText("Proje durdu")).toBeTruthy();

    // 42'nin kosusu var; 43'un kosusu yok, 44 H6 degil: tek kontrol gorunur.
    const triggers = await screen.findAllByRole("button", { name: "Bu bildirimi ertele" });
    expect(triggers).toHaveLength(1);

    fireEvent.click(triggers[0]);
    // Menu basligi kosunun "neden simdi"si: hangi satir oldugu kaybolmaz.
    expect(await screen.findByText("projede 16 gündür kayıtlı anlamlı aktivite yok")).toBeTruthy();

    const threeDays = await screen.findByRole("menuitem", { name: "3 gün sonra" });
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-09-21T10:00:00.000Z"));
    fireEvent.click(threeDays);

    await waitFor(() => {
      expect(lastCall("POST", "/api/proactivity/runs/7/snooze")?.body).toEqual({
        until: "2026-09-24T10:00:00.000Z",
      });
    });
  });
});
