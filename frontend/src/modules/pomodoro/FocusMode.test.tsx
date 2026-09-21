// @vitest-environment jsdom

/**
 * Odak modu sayacı CANLI olmalı: bu tam ekran katmanda başka hiçbir ipucu yok,
 * sayı kendini her saniye güncellemezse ekran donmuş görünür.
 *
 * Kayıt: sayaç effect'i bir ara başka bir effect'in GÖVDESİNDE çağrılıyordu
 * (iç içe hook), yani hiç kaydolmuyordu; statik render testi bunu göremediği
 * için regresyon burada gerçek zamanla korunuyor.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import type { PomodoroSession } from "@/core/types";
import { FocusMode } from "./FocusMode";

vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));

import { api } from "@/core/api";

const apiGet = vi.mocked(api.get);

/** 10 saniye önce başlamış 50 dakikalık seans: kalan 49:50. */
function session(): PomodoroSession {
  return {
    id: "pomo-1",
    started_at: new Date(Date.now() - 10_000).toISOString(),
    ended_at: null,
    planned_min: 50,
    actual_min: null,
    kind: "focus",
    context_entity_id: null,
    context_title: null,
    context_type: null,
    topic: "Derin çalışma",
    interrupted: false,
    paused_at: null,
    paused_s: 0,
  };
}

beforeEach(() => {
  apiGet.mockReset();
  apiGet.mockImplementation(async () => session());
});

afterEach(cleanup);

describe("odak modu sayacı", () => {
  it("kalan süreyi her saniye tazeler", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <FocusMode onClose={() => {}} />
        </ToastProvider>
      </QueryClientProvider>,
    );

    const digit = () => screen.getByText(/^\d\d:\d\d$/).textContent;
    await waitFor(() => expect(digit()).toBe("49:50"));

    // Gerçek 1 sn'lik tik: değer kendiliğinden değişmeli (müdahale yok).
    await waitFor(() => expect(digit()).not.toBe("49:50"), { timeout: 3_000 });
  });
});
