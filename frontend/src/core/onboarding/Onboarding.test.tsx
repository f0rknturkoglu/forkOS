// @vitest-environment jsdom
import "@/modules";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { TutorialTestMode } from "./TutorialTestMode";
import { OnboardingHost } from "./OnboardingHost";
import { SourceDiscovery } from "./SourceDiscovery";
import { experienceFixture } from "./testFixtures";
import { ToastProvider } from "@/core/ui";
import { api } from "@/core/api";
import { tourSteps } from "./catalog";
import { hydrateSettings } from "@/core/registry";
import { useFeedStream, composeFeed, type StreamItem } from "@/core/feedStream";
import { renderHook } from "@testing-library/react";
vi.mock("@/core/api", () => ({ api: { get: vi.fn(), put: vi.fn(), post: vi.fn() }, qs: () => "" }));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/app/router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/app/router")>()),
  useHashRoute: () => ({ path: "/todos", params: new URLSearchParams() }),
  navigate: vi.fn(),
}));
let current = experienceFixture([], false);
let fail = false;
function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  );
}
beforeEach(() => {
  vi.resetAllMocks();
  current = experienceFixture([], false);
  fail = false;
  hydrateSettings({});
  vi.mocked(api.get).mockImplementation(async (path) => {
    if (path === "/system/experience") {
      if (fail) throw new Error("offline");
      return structuredClone(current);
    }
    return [];
  });
  vi.mocked(api.put).mockImplementation(async (_path, body) => {
    const change = body as { feed?: typeof current.feed; onboarding?: typeof current.onboarding; revision: string };
    if (change.revision !== current.revision) throw new Error("Tercihler başka sekmede değişti");
    current = { ...current, ...change, revision: "b".repeat(64), first_run: false };
    return current;
  });
});
afterEach(() => {
  cleanup();
  localStorage.clear();
});
it("existing and offline installations never automatically show Welcome", async () => {
  const show = render(<OnboardingHost />, { wrapper });
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(screen.queryByRole("dialog")).toBeNull();
  show.unmount();
  fail = true;
  render(<OnboardingHost />, { wrapper });
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
  expect(screen.queryByRole("dialog")).toBeNull();
});
it("fresh Welcome persists journey and explicit skip; no provider requests", async () => {
  current.first_run = true;
  render(<OnboardingHost />, { wrapper });
  fireEvent.click(await screen.findByRole("button", { name: "Başlayalım" }));
  fireEvent.click(await screen.findByRole("button", { name: "Günümü düzenlemek" }));
  fireEvent.click(await screen.findByRole("button", { name: "Kaynakları şimdilik geç" }));
  await waitFor(() => expect(current.onboarding.feed_setup).toBe("skipped"));
  expect(current.onboarding.journey).toBe("planning");
  expect(current.feed.providers).toEqual([]);
  expect(vi.mocked(api.get).mock.calls.every(([path]) => !path.startsWith("/news/"))).toBe(true);
});
it("pending source selection is immediate and does not commit or fetch; explicit save persists", async () => {
  const closed = vi.fn();
  render(<SourceDiscovery onClose={closed} />, { wrapper });
  fireEvent.click(await screen.findByRole("button", { name: "Hacker News ekle" }));
  expect(screen.getByRole("button", { name: "Hacker News çıkar" }).getAttribute("aria-pressed")).toBe("true");
  expect(api.put).not.toHaveBeenCalled();
  expect(current.feed.providers).toEqual([]);
  fireEvent.click(screen.getByRole("button", { name: "Seçimleri kaydet" }));
  await waitFor(() => expect(current.feed.providers).toEqual(["hn"]));
  expect(closed).toHaveBeenCalled();
});
it("an open editor preserves its original revision and reports concurrent edits", async () => {
  render(<SourceDiscovery onClose={vi.fn()} />, { wrapper });
  fireEvent.click(await screen.findByRole("button", { name: "Hacker News ekle" }));
  current = { ...current, revision: "c".repeat(64), feed: { ...current.feed, providers: ["hf"] } };
  fireEvent.click(screen.getByRole("button", { name: "Seçimleri kaydet" }));
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(current.feed.providers).toEqual(["hf"]);
});
it("tour routes follow registry and disabled modules disappear", () => {
  expect(tourSteps("planning").map((s) => s.id)).toEqual(["planning", "planner", "home"]);
  hydrateSettings({ "modules.disabled": ["todo"] });
  expect(tourSteps("planning").map((s) => s.id)).toEqual(["home"]);
});
it("new installation cannot fetch disabled channels even when All is visible", async () => {
  const { result } = renderHook(() => useFeedStream("all"), { wrapper });
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current.sources).toEqual([]);
  expect(vi.mocked(api.get).mock.calls.map(([path]) => path)).toEqual(["/system/experience"]);
});
it("dedup keeps provider diversity while stripping tracking identity", () => {
  const item = (key: string, url: string, origin: StreamItem["origin"]): StreamItem => ({
    key,
    title: key,
    href: url,
    origin,
    source: key,
    subtitle: null,
    host: null,
    score: null,
    scoreIcon: null,
    commentsUrl: null,
    at: 0,
    unread: false,
  });
  const output = composeFeed(
    [
      [item("hn", "https://example.com/a?utm_source=hn", "hn"), item("hn2", "https://example.com/b", "hn")],
      [item("rss", "https://example.com/a", "rss"), item("rss2", "https://example.com/c", "rss")],
      [item("paper", "https://arxiv.org/abs/2610.11216", "hf")],
    ],
    4,
  );
  expect(output.map((i) => i.key)).toEqual(["hn", "paper", "hn2", "rss2"]);
});
it("persisted tour waits for a lazy target, respects navigation guard and restores focus", async () => {
  current.onboarding = {
    ...current.onboarding,
    status: "in_progress",
    phase: "tour",
    active_tour: "planning",
    active_step: "planning",
    journey: "planning",
    feed_setup: "skipped",
  };
  const page = render(
    <>
      <button aria-label="Bu sayfa hakkında bilgi ve rehberler">i</button>
      <OnboardingHost />
    </>,
    { wrapper },
  );
  const next = await screen.findByRole("button", { name: "Sonraki" });
  expect(next.hasAttribute("disabled")).toBe(true);
  page.rerender(
    <>
      <button aria-label="Bu sayfa hakkında bilgi ve rehberler">i</button>
      <div data-onboarding="todo-create">
        <button>Gerçek kontrol</button>
      </div>
      <OnboardingHost />
    </>,
  );
  await waitFor(() => expect(screen.getByRole("button", { name: "Sonraki" }).hasAttribute("disabled")).toBe(false));
  const block = (event: Event) => event.preventDefault();
  window.addEventListener("forkos:before-navigation", block);
  fireEvent.click(screen.getByRole("button", { name: "Sonraki" }));
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(api.put).not.toHaveBeenCalled();
  window.removeEventListener("forkos:before-navigation", block);
  fireEvent.click(screen.getByRole("button", { name: "Adıma git" }));
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "Gerçek kontrol" }));
  fireEvent.click(screen.getByRole("button", { name: "Rehberi küçült" }));
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "Bu sayfa hakkında bilgi ve rehberler" }));
  expect(screen.getByRole("button", { name: "Rehbere devam et" })).toBeTruthy();
  expect(current.onboarding.active_step).toBe("planning");
});

it("tutorial can repeatedly restart Welcome while preserving chosen sources and existing content counts", async () => {
  current.onboarding = {
    ...current.onboarding,
    status: "completed",
    visited_steps: ["old-step"],
    skipped_steps: ["old-skip"],
  };
  current.counts = { goals: 3, todos: 5 };
  const feed = structuredClone(current.feed);
  render(
    <>
      <TutorialTestMode />
      <OnboardingHost />
    </>,
    { wrapper },
  );
  fireEvent.click(await screen.findByRole("checkbox", { name: "Tutorial deneme modu" }));
  const start = screen.getByRole("button", { name: "Tutorialı sıfırdan başlat" });
  await waitFor(() => expect(start.hasAttribute("disabled")).toBe(false));
  fireEvent.click(start);
  await screen.findByRole("dialog", { name: "forkOS’a hoş geldin" });
  expect(current.onboarding.visited_steps).toEqual([]);
  expect(current.onboarding.skipped_steps).toEqual([]);
  expect(current.feed).toEqual(feed);
  expect(current.counts).toEqual({ goals: 3, todos: 5 });
  fireEvent.click(screen.getByRole("button", { name: "Sonra keşfederim" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  fireEvent.click(start);
  await screen.findByRole("dialog", { name: "forkOS’a hoş geldin" });
  expect(current.feed).toEqual(feed);
});
it("explicit bundle repair preserves pending provider choices and advances the CAS baseline", async () => {
  const missing = "00000000-0000-4000-8000-000000000001";
  current = {
    ...current,
    invalid_feed_ids: [missing],
    feed: {
      ...current.feed,
      bundles: [{ id: "00000000-0000-4000-8000-000000000002", title: "Keep", channels: [], feed_ids: [missing] }],
    },
  };
  vi.mocked(api.post).mockImplementation(async (path) => {
    expect(path).toBe("/system/experience/repair");
    current = {
      ...current,
      invalid_feed_ids: [],
      revision: "d".repeat(64),
      feed: { ...current.feed, bundles: current.feed.bundles.map((b) => ({ ...b, feed_ids: [] })) },
    };
    return structuredClone(current);
  });
  render(<SourceDiscovery onClose={vi.fn()} />, { wrapper });
  fireEvent.click(await screen.findByRole("button", { name: "Hacker News ekle" }));
  fireEvent.click(screen.getByRole("button", { name: "Seçki üyeliklerini onar" }));
  await screen.findByText("Seçki üyelikleri onarıldı");
  fireEvent.click(screen.getByRole("button", { name: "Seçimleri kaydet" }));
  await waitFor(() => expect(current.feed.providers).toEqual(["hn"]));
  expect(current.feed.bundles[0].feed_ids).toEqual([]);
});
