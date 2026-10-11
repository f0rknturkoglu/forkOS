// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { experienceFixture } from "@/core/onboarding/testFixtures";
import { FeedStreamWidget } from "./FeedStreamWidget";

const harness = vi.hoisted(() => ({
  hnRefetch: vi.fn(),
  rssLoading: false,
  rssEmpty: false,
  hnLoading: false,
}));

vi.mock("@/core/api", () => ({
  api: { get: vi.fn() },
  qs: () => "?limit=15",
}));

vi.mock("@/app/router", () => ({ navigate: vi.fn() }));

vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(({ queryKey }: { queryKey: string[] }) => {
    const key =
      queryKey[0] === "settings" && queryKey[1] === "feed"
        ? ({ hn: "hacker-news", gh: "github-trending", hf: "papers", reddit: "reddit-news" } as Record<string, string>)[
            queryKey[2]
          ]
        : queryKey[0];
    switch (key) {
      case "settings":
        return { data: experienceFixture(), isPending: false, isLoading: false, isError: false };
      case "items":
        return {
          data:
            harness.rssLoading || harness.rssEmpty
              ? []
              : [
                  {
                    id: "rss-1",
                    feed_id: "feed-1",
                    feed_title: "Yerel RSS",
                    title: "RSS çalışıyor",
                    published_at: "2026-08-29T08:00:00Z",
                    fetched_at: "2026-08-29T08:00:00Z",
                    read_at: null,
                  },
                ],
          isLoading: harness.rssLoading,
          isError: false,
          refetch: vi.fn(),
        };
      case "rss-stats":
        return { data: { unread: 1 }, isError: false, refetch: vi.fn() };
      case "papers":
      case "reddit-news":
        return { data: [], isError: false, refetch: vi.fn() };
      case "hacker-news":
        return { data: [], isLoading: harness.hnLoading, isError: !harness.hnLoading, refetch: harness.hnRefetch };
      case "github-trending":
        return {
          data: [
            {
              full_name: "forkOS/repo",
              html_url: "https://github.com/forkOS/repo",
              description: "Yerel yaşam sistemi",
              stargazers_count: 42,
              language: "TypeScript",
              created_at: "2026-08-29T09:00:00Z",
            },
          ],
          isError: false,
          refetch: vi.fn(),
        };
      default:
        throw new Error(`Beklenmeyen query: ${queryKey[0]}`);
    }
  }),
}));

describe("FeedStreamWidget source isolation", () => {
  afterEach(() => {
    cleanup();
    harness.hnRefetch.mockReset();
    harness.rssLoading = false;
    harness.rssEmpty = false;
    harness.hnLoading = false;
  });

  it("bir kaynak hata verirken digerlerini gosterir ve yalniz o kaynagi yeniden dener", () => {
    render(<FeedStreamWidget />);

    expect(screen.getByText("RSS çalışıyor")).toBeTruthy();
    expect(screen.getByText("forkOS/repo")).toBeTruthy();
    expect(screen.getByText(/Hacker News alınamadı/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Hacker News'i yeniden dene" }));
    expect(harness.hnRefetch).toHaveBeenCalledTimes(1);
  });

  it("filtre secimini aria-pressed ile aktarir ve yalniz secili kaynak yuklenirken yukleniyor der", () => {
    harness.rssLoading = true;
    render(<FeedStreamWidget />);

    const rss = screen.getByRole("button", { name: "RSS" });
    expect(rss.getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(rss);
    expect(rss.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("Akış yükleniyor…")).toBeTruthy();
  });

  it("unrelated source is loading does not mask a resolved empty selected feed", () => {
    harness.rssEmpty = true;
    harness.hnLoading = true;
    render(<FeedStreamWidget />);

    fireEvent.click(screen.getByRole("button", { name: "RSS" }));
    expect(screen.getByText("Yeni bir şey yok.")).toBeTruthy();
    expect(screen.queryByText("Akış yükleniyor…")).toBeNull();
  });
});
