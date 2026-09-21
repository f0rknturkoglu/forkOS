// @vitest-environment jsdom

/**
 * §63/§64: baslik gostergesi yalniz aktif seans varken cizilir ve tiklamak
 * odak kontrollerini acar. Oturum yokken baslikta yer KAPLAMAZ.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import type { PomodoroSession } from "@/core/types";
import { ActiveFocusIndicator } from "./ActiveFocusIndicator";
import { QuickActionDock } from "./PomodoroDock";

vi.mock("@/lib/hooks", () => ({
  useOnline: () => true,
  useDebounced: (value: string) => value,
}));
vi.mock("@/core/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), del: vi.fn() },
  qs: vi.fn(() => ""),
}));

import { api } from "@/core/api";

const apiGet = vi.mocked(api.get);

function session(paused: boolean): PomodoroSession {
  // Kalan sure sabit olsun diye baslangic "simdi": 50 dk - 0 sn = 50:00.
  return {
    id: "pomo-1",
    started_at: new Date().toISOString(),
    ended_at: null,
    planned_min: 50,
    actual_min: null,
    kind: "focus",
    context_entity_id: null,
    context_title: null,
    context_type: null,
    topic: "Derin çalışma",
    interrupted: false,
    paused_at: paused ? new Date().toISOString() : null,
    paused_s: 0,
  };
}

beforeEach(() => {
  apiGet.mockReset();
});

afterEach(cleanup);

function renderIndicator() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <ActiveFocusIndicator />
        <QuickActionDock />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("baslik aktif odak gostergesi", () => {
  it("oturum yokken hicbir sey cizmez", async () => {
    apiGet.mockImplementation(async (path: string) => {
      if (path === "/pomodoro/active") return null;
      if (path.startsWith("/pomodoro/stats")) return { minutes: 0, sessions: 0, interrupted: 0 };
      return [];
    });

    const { container } = renderIndicator();

    await screen.findByRole("button", { name: "Hızlı işlem menüsünü aç" });
    expect(container.querySelector('[aria-label^="Aktif odak:"]')).toBeNull();
    expect(screen.queryByRole("button", { name: /^Aktif odak:/ })).toBeNull();
  });

  it("calisan oturumda sureyi ve durumu gosterir, tiklayinca odak kontrollerini acar", async () => {
    apiGet.mockImplementation(async (path: string) => {
      if (path === "/pomodoro/active") return session(false);
      if (path.startsWith("/pomodoro/stats")) return { minutes: 0, sessions: 0, interrupted: 0 };
      return [];
    });

    renderIndicator();

    const indicator = await screen.findByRole("button", {
      name: /^Aktif odak: Derin çalışma, \d\d:\d\d, çalışıyor$/,
    });
    expect(indicator.className).toContain("h-8");

    fireEvent.click(indicator);

    const panel = await screen.findByRole("dialog", { name: "Aktif odak seçenekleri" });
    expect(within(panel).getByRole("button", { name: /duraklat/ })).toBeTruthy();
    expect(within(panel).getByRole("button", { name: /tamamla/ })).toBeTruthy();
  });

  it("duraklatilmis oturumda duraklatildi der", async () => {
    apiGet.mockImplementation(async (path: string) => {
      if (path === "/pomodoro/active") return session(true);
      if (path.startsWith("/pomodoro/stats")) return { minutes: 0, sessions: 0, interrupted: 0 };
      return [];
    });

    renderIndicator();

    expect(
      await screen.findByRole("button", { name: /^Aktif odak: Derin çalışma, \d\d:\d\d, duraklatıldı$/ }),
    ).toBeTruthy();
  });
});
