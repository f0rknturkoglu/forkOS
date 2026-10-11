// @vitest-environment jsdom
/**
 * Home istek sözleşmesi (P4 §38/§40, P2 §13-§19).
 *
 * Home'un çekirdek yüzeyleri KÜÇÜK ve öngörülebilir bir uç kümesi kullanır:
 * aynı uç farklı parametrelerle iki kez çağrılmaz ve sayfa açılışı sınırlı
 * sayıda istek üretir. Bu test fan-out'un sessizce geri gelmesini engeller.
 *
 * Ölçüm gerçek render üzerinden yapılır (fetch kaydı); statik tahmin değildir.
 * Çekirdek iskelet: bekleyen kararlar, bugünün planı, son tarihler, kariyer,
 * okuma akışı, öğrenme ve ısı haritası.
 */
import "@/modules";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { allTodayWidgets, setTodayWidgetHidden } from "@/core/registry";
import { ToastProvider } from "@/core/ui";
import { TodayPage } from "./TodayPage";

vi.hoisted(() => {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => store.set(key, value),
      removeItem: (key: string) => store.delete(key),
      clear: () => store.clear(),
    },
  });
});

interface Recorded {
  method: string;
  path: string;
}

let calls: Recorded[] = [];

const AGENDA = {
  day: "2026-01-01",
  timed: [
    {
      kind: "todo",
      source: "planned",
      id: "timed-1",
      slot_id: "slot-1",
      title: "Sıradaki iş",
      completed: false,
      action: "complete_todo",
      read_only: false,
      context_only: false,
      starts_at: new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString(),
      duration_min: 30,
      parent_id: null,
      project_title: null,
      feed_title: null,
      url: null,
      recur: null,
      progress_label: null,
      children: [],
    },
  ],
  checklist: [],
  completed: [],
  auto_suggestions: true,
  suggestions: { todos: [], rss: [], flashcards: [], study: [], career: [] },
};

/** Uç bazlı asgari gövde: şekil bilinmiyorsa boş liste Home için güvenlidir. */
function bodyFor(path: string): unknown {
  if (path.startsWith("/api/today/agenda")) return AGENDA;
  if (path.startsWith("/api/settings")) return {};
  return [];
}

/** Çekirdek yüzeylerin dokunduğu uçlar: biri düşerse Home eksik kalır. */
const CORE_ENDPOINTS = [
  "/api/execution/plans",
  "/api/today/agenda",
  "/api/todos",
  "/api/plan",
  "/api/deadlines",
  "/api/opportunities/followups",
  "/api/notifications",
  "/api/rss/items",
  "/api/news/reddit",
  "/api/news/hacker-news",
  "/api/news/github-trending",
  "/api/courses",
  "/api/study/stale",
  "/api/activity/heatmap",
];

describe("Home istek sözleşmesi", () => {
  beforeEach(() => {
    calls = [];
    localStorage.clear();
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = new URL(String(input), "http://localhost");
        const path = url.pathname + url.search;
        calls.push({ method: init?.method ?? "GET", path });
        return new Response(JSON.stringify(bodyFor(path)), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("çekirdek yüzeyleri yükler, aynı isteği tekrarlamaz", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <TodayPage />
        </ToastProvider>
      </QueryClientProvider>,
    );

    await waitFor(() => expect(calls.length).toBeGreaterThan(0));
    // Sorgular yerleşene kadar kısa bir pencere bekle.
    await waitFor(() => expect(new Set(calls.map((call) => call.path)).size).toBeGreaterThan(8));

    const gets = calls.filter((call) => call.method === "GET");
    const uniquePaths = new Set(gets.map((call) => call.path));
    // Aynı yol+parametre iki kez istenmez (paylaşılan anahtar sözleşmesi).
    expect(gets.length).toBe(uniquePaths.size);
    // Çekirdek iskelet bounded kalır: 7 yüzey + hero sayaçları.
    expect(uniquePaths.size).toBeLessThanOrEqual(20);
    for (const prefix of CORE_ENDPOINTS) {
      expect([...uniquePaths].some((path) => path.startsWith(prefix))).toBe(true);
    }
  });

  it("widget tercihi değişince Home aynı oturumda güncellenir (reload yok)", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <TodayPage />
        </ToastProvider>
      </QueryClientProvider>,
    );

    // İsteğe bağlı yüzey görünür: "Şimdi ve sırada".
    await waitFor(() => expect(screen.queryByText("Şimdi ve sırada")).toBeTruthy());

    // Ayarlar > Home aynı anda yazar; Home yeniden mount edilmeden güncellenir.
    act(() => setTodayWidgetHidden(["today.now-next"]));
    await waitFor(() => expect(screen.queryByText("Şimdi ve sırada")).toBeNull());

    // Çekirdek yüzeyler gizleme listesinden etkilenmez: isteğe bağlı katman
    // tamamen gizlense bile iskelet ayakta kalır.
    const optionalIds = allTodayWidgets()
      .filter((widget) => !widget.core)
      .map((widget) => widget.id);
    act(() => setTodayWidgetHidden([...optionalIds, "today.agenda"]));
    expect(screen.queryByText("Bugünün planı")).toBeTruthy();
    expect(screen.queryByText("Şimdi ve sırada")).toBeNull();
  });
});
