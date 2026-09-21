// @vitest-environment jsdom
/**
 * Home istek sözleşmesi (P4 §38/§40).
 *
 * Home'un temiz kurulumdaki yüzeyleri KÜÇÜK ve öngörülebilir bir uç kümesi
 * kullanmalıdır: aynı uç farklı parametrelerle iki kez çağrılmaz ve sayfa
 * açılışı sınırlı sayıda istek üretir. Bu test fan-out'un sessizce geri
 * gelmesini engeller.
 *
 * Ölçüm gerçek render üzerinden yapılır (fetch kaydı); statik tahmin değildir.
 *
 * Ürünleştirme öncesi aynı ölçüm 22 ayrı uç gösteriyordu (akış, emek haritası,
 * ritim, kart, gelen kutusu, öğrenme, üç fırsat widget'ı ...). Home v2 sonrası
 * temiz kurulumda çağrılan uçlar:
 *   /api/execution/plans, /api/today/agenda, /api/todos, /api/plan,
 *   /api/activity, /api/reviews, /api/deadlines, /api/opportunities/followups,
 *   /api/notifications, /api/bookmarks/stats, /api/rss/stats
 */
import "@/modules";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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
  timed: [],
  checklist: [],
  completed: [],
  auto_suggestions: true,
  suggestions: { todos: [], rss: [], media: [], flashcards: [], study: [], career: [] },
};

/** Uç bazlı asgari gövde: şekil bilinmiyorsa boş liste Home için güvenlidir. */
function bodyFor(path: string): unknown {
  if (path.startsWith("/api/today/agenda")) return AGENDA;
  if (path.startsWith("/api/settings")) return {};
  return [];
}

describe("Home istek sözleşmesi", () => {
  beforeEach(() => {
    calls = [];
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

  afterEach(() => vi.unstubAllGlobals());

  it("temiz kurulumda sınırlı sayıda uç çağırır ve aynı isteği tekrarlamaz", async () => {
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
    await waitFor(() => expect(new Set(calls.map((call) => call.path)).size).toBeGreaterThan(3));

    const gets = calls.filter((call) => call.method === "GET");
    const uniquePaths = new Set(gets.map((call) => call.path));
    // Aynı yol+parametre iki kez istenmez (paylaşılan anahtar sözleşmesi).
    expect(gets.length).toBe(uniquePaths.size);
    // Temiz kurulum Home'u bounded kalır: 4 yüzey + hero sayaçları.
    expect(uniquePaths.size).toBeLessThanOrEqual(12);
    // Dört yürütme yüzeyi gerçekten yüklü: biri sessizce düşerse test kırılır.
    for (const prefix of [
      "/api/execution/plans",
      "/api/today/agenda",
      "/api/deadlines",
      "/api/opportunities/followups",
      "/api/notifications",
    ]) {
      expect([...uniquePaths].some((path) => path.startsWith(prefix))).toBe(true);
    }
  });
});
