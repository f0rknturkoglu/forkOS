// @vitest-environment jsdom

/**
 * H6 kontrol bolumu sozlesmesi: durum + kural listesi yuklenir, ana anahtar ve
 * esik yazmalari dogru uca gider, erteleme on ayari mutlak ISO zaman uretir.
 * Gercek ag yok; `fetch` kaydedici bir stub'dur.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import type { ProactivityRun } from "@/core/proactivity";
import { ProactivitySection } from "./ProactivitySection";

interface Call {
  method: string;
  path: string;
  body?: Record<string, unknown>;
}

let calls: Call[] = [];
/** Test basina degistirilebilen kosu listesi; RUNS tanimindan sonra atanir. */
let runs: ProactivityRun[];

function json(value: unknown): Response {
  return new Response(JSON.stringify(value), { status: 200, headers: { "Content-Type": "application/json" } });
}

function lastCall(method: string, path: string): Call | undefined {
  return [...calls].reverse().find((call) => call.method === method && call.path === path);
}

type Rule = {
  kind: string;
  version: number;
  logical_key: string;
  enabled: boolean;
  config: Record<string, unknown>;
  snoozed_until: string | null;
};

function rule(kind: string, enabled: boolean, config: Record<string, unknown>): Rule {
  return { kind, version: 1, logical_key: `${kind}:v1:global`, enabled, config, snoozed_until: null };
}

/** Backend `service.RULE_DEFAULTS` ile ayni kume ve varsayilanlar. */
const RULES: Rule[] = [
  rule("morning_continuity", false, { time: "08:05", grace_hours: 4 }),
  rule("daily_close", false, { time: "21:00", grace_hours: 3 }),
  rule("weekly_review", false, { weekday: 6, time: "18:00", grace_hours: 24 }),
  rule("deadline_staircase", true, {}),
  rule("continuity_gap", false, { threshold_hours: 48 }),
  rule("project_stalled", false, { days: 14, cooldown_days: 7 }),
];

const STATUS = {
  enabled: false,
  quiet_hours_start: "23:30",
  quiet_hours_end: "08:30",
  focus_deferral_enabled: true,
  digest_time: "18:30",
  immediate_budget: 3,
  immediate_surfaces_today: 1,
  pending_deferred: 2,
  pending_digest: 0,
  worker_heartbeat: { at: "2026-09-21T09:00:00+00:00" },
  last_run_at: "2026-09-21T09:05:00+00:00",
  rules: RULES,
  recent_failures: [],
};

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
  {
    id: 8,
    rule_kind: "continuity_gap",
    subject_type: null,
    subject_id: null,
    state: "snoozed",
    reason_codes: ["CONTINUITY_GAP"],
    why_now: null,
    triggered_at: "2026-09-20T09:00:00+00:00",
    delivered_at: null,
    delivery_count: 0,
    snoozed_until: "2026-09-24T09:00:00+00:00",
    notification_id: null,
    failure_code: null,
  },
];

runs = RUNS;

function renderSection() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <ProactivitySection online />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  calls = [];
  runs = RUNS;
  Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const method = (init?.method ?? "GET").toUpperCase();
      calls.push({ method, path: url.pathname, body: init?.body ? JSON.parse(String(init.body)) : undefined });

      if (url.pathname === "/api/proactivity/status") return json(STATUS);
      if (url.pathname === "/api/proactivity/rules") return json(RULES);
      if (url.pathname === "/api/proactivity/history") return json(runs);
      if (url.pathname === "/api/proactivity/config" && method === "PUT") return json(STATUS);
      if (url.pathname.startsWith("/api/proactivity/rules/") && method === "PUT") return json(RULES[0]);
      if (url.pathname.endsWith("/snooze")) return json(RUNS);
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

describe("ProactivitySection", () => {
  it("durumu yükleyip ana anahtarı, kural listesini ve son koşuları gösterir", async () => {
    renderSection();

    const master = await screen.findByRole("checkbox", { name: "Proaktif müdahale açık" });
    expect((master as HTMLInputElement).checked).toBe(false);

    // Kapali kural kumesi etiketleriyle gelir (ham `kind` degil).
    expect(await screen.findByRole("checkbox", { name: "Son tarih basamakları" })).toBeTruthy();
    expect(screen.getByRole("checkbox", { name: "Durmuş projeler" })).toBeTruthy();
    expect(screen.getByRole("checkbox", { name: "Sessizlik sonrası dönüş" })).toBeTruthy();

    // Durum ozeti + kosu gecmisi.
    expect(screen.getByText("bekleyen erteleme")).toBeTruthy();
    expect(screen.getByText("projede 16 gündür kayıtlı anlamlı aktivite yok")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Bu koşuyu ertele" })).toBeTruthy();
    // Erteleme zaten varsa geri alma aksiyonu gosterilir.
    expect(screen.getByRole("button", { name: "Ertelemeyi kaldır" })).toBeTruthy();
  });

  it("uzun kosu gecmisini asamali acilimla sinirlar (kayit kaybi yok)", async () => {
    runs = Array.from({ length: 7 }, (_, index) => ({ ...RUNS[0], id: 100 + index, why_now: `kosu ${index + 1}` }));
    renderSection();
    await screen.findByText("Son koşular");

    // Ilk 5 satir acik; gerisi katlanir, ama sayisi gorunur kalir.
    expect(screen.getByText("kosu 1")).toBeTruthy();
    expect(screen.getByText("kosu 5")).toBeTruthy();
    expect(screen.queryByText("kosu 6")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Tüm koşular \(7\)/ }));
    expect(await screen.findByText("kosu 6")).toBeTruthy();
    expect(screen.getByText("kosu 7")).toBeTruthy();
  });

  it("ana anahtar değişince PUT /proactivity/config çağırır", async () => {
    renderSection();

    fireEvent.click(await screen.findByRole("checkbox", { name: "Proaktif müdahale açık" }));

    await waitFor(() => {
      expect(lastCall("PUT", "/api/proactivity/config")?.body).toEqual({ enabled: true });
    });
  });

  it("kural eşiği alandan çıkınca PUT /proactivity/rules/{kind} çağırır", async () => {
    renderSection();

    const threshold = await screen.findByRole("spinbutton", { name: "Sessizlik eşiği (saat)" });
    fireEvent.change(threshold, { target: { value: "72" } });
    fireEvent.blur(threshold, { target: { value: "72" } });

    await waitFor(() => {
      expect(lastCall("PUT", "/api/proactivity/rules/continuity_gap")?.body).toEqual({
        config: { threshold_hours: 72 },
      });
    });
  });

  it("'3 gün' ön ayarını mutlak ISO zamanla POST eder", async () => {
    renderSection();

    fireEvent.click(await screen.findByRole("button", { name: "Bu koşuyu ertele" }));
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

  it("ertelenmiş koşuda ertelemeyi kaldırır", async () => {
    renderSection();

    fireEvent.click(await screen.findByRole("button", { name: "Ertelemeyi kaldır" }));

    await waitFor(() => {
      expect(lastCall("DELETE", "/api/proactivity/runs/8/snooze")).toBeTruthy();
    });
  });

  it("'Bu hafta dürtme' kuralı yedi gün susturur", async () => {
    renderSection();

    const silence = await screen.findAllByRole("button", { name: "Bu hafta dürtme" });
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-09-21T10:00:00.000Z"));
    fireEvent.click(silence[0]);

    await waitFor(() => {
      expect(lastCall("POST", "/api/proactivity/rules/morning_continuity/snooze")?.body).toEqual({
        until: "2026-09-28T10:00:00.000Z",
      });
    });
  });
});
