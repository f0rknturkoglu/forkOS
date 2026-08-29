// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FeedStreamWidget } from "./FeedStreamWidget";

const harness = vi.hoisted(() => ({
  hnRefetch: vi.fn(),
}));

vi.mock("@/core/api", () => ({
  api: { get: vi.fn() },
  qs: () => "?limit=15",
}));

vi.mock("@/app/router", () => ({ navigate: vi.fn() }));

vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(({ queryKey }: { queryKey: string[] }) => {
    switch (queryKey[0]) {
      case "items":
        return {
          data: [
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
          isError: false,
          refetch: vi.fn(),
        };
      case "rss-stats":
        return { data: { unread: 1 }, isError: false, refetch: vi.fn() };
      case "reddit-news":
        return { data: [], isError: false, refetch: vi.fn() };
      case "hacker-news":
        return { data: [], isError: true, refetch: harness.hnRefetch };
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
  });

  it("bir kaynak hata verirken digerlerini gosterir ve yalniz o kaynagi yeniden dener", () => {
    render(<FeedStreamWidget />);

    expect(screen.getByText("RSS çalışıyor")).toBeTruthy();
    expect(screen.getByText("forkOS/repo")).toBeTruthy();
    expect(screen.getByText(/Hacker News alınamadı/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Hacker News'i yeniden dene" }));
    expect(harness.hnRefetch).toHaveBeenCalledTimes(1);
  });
});
