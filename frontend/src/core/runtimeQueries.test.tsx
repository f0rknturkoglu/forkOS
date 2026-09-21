// @vitest-environment jsdom

/**
 * Paylasilan runtime sorgulari: AYNI uc, TEK anahtar.
 *
 * Kabukta surekli mount olan bilesenler (StatusLed, SourceAlert) ayni kaynak
 * sagligi ucunu farkli anahtarlarla soruyordu; TanStack anahtar basina
 * onbellek kurdugu icin uç oturum boyunca IKI kez yoklanıyordu. Bu testler
 * bunu gorunur davranis uzerinden kilitler: kac istek cikti?
 */

import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import { render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/core/api";
import { queryClient } from "@/core/queryClient";
import {
  SOURCE_HEALTH_INTERVAL_MS,
  SOURCE_HEALTH_QUERY_KEY,
  useSourceHealth,
  useSystemStats,
} from "@/core/runtimeQueries";
import type { SourceHealth } from "@/core/types";

const harness = vi.hoisted(() => ({ urls: [] as string[] }));

vi.stubGlobal(
  "fetch",
  vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    harness.urls.push(new URL(url, "http://localhost").pathname + new URL(url, "http://localhost").search);
    const body = url.includes("/sources/health") ? ([] as SourceHealth[]) : { worker: { status: "disabled" } };
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }),
);

function Both() {
  useSourceHealth();
  useSystemStats();
  return null;
}

function renderWithClient(ui: React.ReactElement) {
  const client = queryClient();
  client.clear();
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("paylasilan runtime sorgulari", () => {
  beforeEach(() => {
    harness.urls.length = 0;
  });

  afterEach(() => {
    queryClient().clear();
  });

  it("ayni ucu kullanan iki bilesen TEK istek cikarir", async () => {
    renderWithClient(
      <>
        <Both />
        <Both />
      </>,
    );

    await waitFor(() => expect(harness.urls.length).toBeGreaterThanOrEqual(2));
    const healthCalls = harness.urls.filter((url) => url.startsWith("/api/sources/health"));
    expect(healthCalls).toHaveLength(1);
  });

  it("saglik anahtari ve araligi tek yerde tanimlidir", () => {
    // Farkli anahtar kullanmak dedupe'u bozar; anahtar sabittir.
    expect(SOURCE_HEALTH_QUERY_KEY).toEqual(["sources", "health", "all"]);
    // Bosta dakikalar degil, dakikalarca yoklanir.
    expect(SOURCE_HEALTH_INTERVAL_MS).toBeGreaterThanOrEqual(60_000);
  });

  it("ayni ucu AYRI anahtarla sormak ikinci istek uretir", async () => {
    // Paylasilan hook'un neden var oldugunu gosterir: yanlis kullanim
    // gercekten fazladan istek cikarir.
    function Divergent() {
      useQuery({
        queryKey: ["sources", "health"],
        queryFn: () => api.get<SourceHealth[]>("/sources/health"),
      });
      return null;
    }

    renderWithClient(
      <>
        <Both />
        <Divergent />
      </>,
    );

    await waitFor(() => expect(harness.urls.length).toBeGreaterThanOrEqual(3));
    expect(harness.urls.filter((url) => url.startsWith("/api/sources/health"))).toHaveLength(2);
  });

  it("queryClient arka plan ve pencere odagi yoklamalarini varsayilan olarak askiya alir", () => {
    const client = queryClient();
    const defaults = client.getDefaultOptions().queries;
    expect(defaults?.refetchOnWindowFocus).toBe(false);
    expect(defaults?.refetchIntervalInBackground).toBe(false);
    expect(defaults?.staleTime).toBe(30_000);
  });
});
