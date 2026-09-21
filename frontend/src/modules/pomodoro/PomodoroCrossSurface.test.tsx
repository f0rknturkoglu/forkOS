// @vitest-environment jsdom

/**
 * §67 capraz yuzey reaktivite testi.
 *
 * Sayfadan baslatilan seans dock'ta ve baslik gostergesinde gorunmeli; dock'tan
 * duraklatilan seans sayfaya yansimali; tamamlanan seans UC yuzeyde birden
 * kaybolmali -- sayfa yenileme olmadan. Bu yuzden testte `invalidateAfter`
 * MOCK'LANMAZ: gercek queryClient kullanilir ve tazeleme tek kanonik anahtar
 * uzerinden (`pomodoro-active`) yayilir.
 */
import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { queryClient } from "@/core/queryClient";
import { ToastProvider } from "@/core/ui";
import type { PomodoroSession, PomodoroStats } from "@/core/types";
import { ActiveFocusIndicator } from "./ActiveFocusIndicator";
import { QuickActionDock } from "./PomodoroDock";
import { PomodoroPage } from "./PomodoroPage";
import { POMODORO_STATS_QUERY_KEY } from "./queries";

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
const apiPost = vi.mocked(api.post);

let session: PomodoroSession | null = null;
let completed = { minutes: 0, sessions: 0 };

/**
 * Bugun istatistigi gozlemcisi: Home'daki Odak widget'i ve Etkinlik
 * istatistikleri ayni anahtari paylasir. Sayilar tamamlanan seanstan sonra
 * tazelenmezse bu yuzeyler sessizce bayat kalir.
 */
function TodayStatsProbe() {
  const { data } = useQuery({
    queryKey: POMODORO_STATS_QUERY_KEY,
    queryFn: () => api.get<PomodoroStats>("/pomodoro/stats?range=day"),
  });
  return <p data-testid="today-stats">{data ? `${data.minutes} dk · ${data.sessions} seans` : "yükleniyor"}</p>;
}

function startedSession(): PomodoroSession {
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
    paused_at: null,
    paused_s: 0,
  };
}

beforeEach(() => {
  session = null;
  completed = { minutes: 0, sessions: 0 };
  apiGet.mockReset();
  apiPost.mockReset();
  apiGet.mockImplementation(async (path: string) => {
    if (path === "/pomodoro/active") return session;
    if (path.startsWith("/pomodoro/stats")) return { ...completed, interrupted: 0 };
    if (path.startsWith("/pomodoro/analytics")) {
      return { minutes: 0, completed: 0, interrupted: 0, daily: [], contexts: [] };
    }
    if (path.startsWith("/pomodoro/contexts")) return [];
    return [];
  });
  apiPost.mockImplementation(async (path: string) => {
    if (path === "/pomodoro/start") {
      session = startedSession();
      return session;
    }
    if (path === "/pomodoro/pomo-1/pause") {
      session = session ? { ...session, paused_at: new Date().toISOString() } : null;
      return session;
    }
    if (path === "/pomodoro/pomo-1/resume") {
      session = session ? { ...session, paused_at: null } : null;
      return session;
    }
    if (path === "/pomodoro/pomo-1/stop") {
      completed = { minutes: completed.minutes + (session?.planned_min ?? 0), sessions: completed.sessions + 1 };
      session = null;
      return {};
    }
    return {};
  });
  queryClient().clear();
  queryClient().setDefaultOptions({ queries: { retry: false, staleTime: 0 } });
});

afterEach(cleanup);

function renderSurfaces() {
  return render(
    <QueryClientProvider client={queryClient()}>
      <ToastProvider>
        <ActiveFocusIndicator />
        <TodayStatsProbe />
        <PomodoroPage />
        <QuickActionDock />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("pomodoro capraz yuzey canli senkron", () => {
  it("sayfadan baslatir, dock'tan duraklatir, dock'tan tamamlar -- reload olmadan", async () => {
    renderSurfaces();

    // Bosta: gosterge yok, dock ince hizli eylem dugmesi, bugun istatistigi sifir.
    expect(screen.queryByRole("button", { name: /^Aktif odak:/ })).toBeNull();
    expect(screen.getByRole("button", { name: "Hızlı işlem menüsünü aç" })).toBeTruthy();
    await waitFor(() => expect(screen.getByTestId("today-stats").textContent).toBe("0 dk · 0 seans"));

    // 1) Sayfadan baslat -> dock ve baslik gostergesi AYNI seansi gosterir.
    fireEvent.click(await screen.findByRole("button", { name: /odaklanmaya başla/ }));

    expect(await screen.findByText("Odak devam ediyor")).toBeTruthy();
    const dockPill = await screen.findByRole("button", { name: /^Odak \d\d:\d\d$/ });
    const indicator = await screen.findByRole("button", { name: /^Aktif odak: Derin çalışma, \d\d:\d\d, çalışıyor$/ });
    expect(indicator.textContent).toContain("Derin çalışma");

    // 2) Dock'tan duraklat -> sayfa ve gosterge duraklatildi durumuna gecer.
    fireEvent.click(dockPill);
    const panel = await screen.findByRole("dialog", { name: "Aktif odak seçenekleri" });
    fireEvent.click(within(panel).getByRole("button", { name: /duraklat/ }));

    expect(await screen.findByText("Odak duraklatıldı")).toBeTruthy();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /^Aktif odak: Derin çalışma, \d\d:\d\d, duraklatıldı$/ })).toBeTruthy(),
    );

    // 2b) Ayni panelden devam et -> hem sayfa hem gosterge yeniden "çalışıyor".
    fireEvent.click(within(panel).getByRole("button", { name: /devam/ }));

    expect(await screen.findByText("Odak devam ediyor")).toBeTruthy();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /^Aktif odak: Derin çalışma, \d\d:\d\d, çalışıyor$/ })).toBeTruthy(),
    );

    // 3) Dock'tan tamamla -> aktif seans yok VE bugun istatistigi tazelenir.
    fireEvent.click(within(panel).getByRole("button", { name: /tamamla/ }));

    expect(await screen.findByText("Yeni odak seansı")).toBeTruthy();
    await waitFor(() => expect(screen.getByRole("button", { name: "Hızlı işlem menüsünü aç" })).toBeTruthy());
    expect(screen.queryByRole("button", { name: /^Aktif odak:/ })).toBeNull();
    await waitFor(() => expect(screen.getByTestId("today-stats").textContent).toBe("50 dk · 1 seans"));
  });

  it("dock'tan yarıda kesilen seans da üç yüzeyden birden düşer", async () => {
    renderSurfaces();

    fireEvent.click(await screen.findByRole("button", { name: /odaklanmaya başla/ }));
    const dockPill = await screen.findByRole("button", { name: /^Odak \d\d:\d\d$/ });

    fireEvent.click(dockPill);
    const panel = await screen.findByRole("dialog", { name: "Aktif odak seçenekleri" });
    fireEvent.click(within(panel).getByRole("button", { name: /yarıda kes/ }));

    expect(await screen.findByText("Yeni odak seansı")).toBeTruthy();
    await waitFor(() => expect(screen.getByRole("button", { name: "Hızlı işlem menüsünü aç" })).toBeTruthy());
    expect(screen.queryByRole("button", { name: /^Aktif odak:/ })).toBeNull();
  });
});
