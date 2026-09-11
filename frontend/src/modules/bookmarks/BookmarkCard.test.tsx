import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Bookmark } from "@/core/types";
import { BookmarkCard } from "./BookmarkCard";

type MutationOptions = {
  mutationFn?: (...args: unknown[]) => unknown;
  onSuccess?: (...args: unknown[]) => void;
};

const harness = vi.hoisted(() => ({
  apiDel: vi.fn(),
  apiPatch: vi.fn(),
  invalidate: vi.fn(),
  mutations: [] as MutationOptions[],
}));

vi.mock("@/core/api", () => ({
  api: { del: harness.apiDel, patch: harness.apiPatch },
}));

vi.mock("@/lib/hooks", () => ({
  useOnline: () => true,
}));

vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));

vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn((options: MutationOptions) => {
    harness.mutations.push(options);
    return {
      isPending: false,
      mutate: vi.fn((...args: unknown[]) => options.mutationFn?.(...args)),
    };
  }),
}));

const mockCardBookmark: Bookmark = {
  id: "bm-card-1",
  url: "https://news.ycombinator.com/item?id=123",
  title: "Show HN: forkOS Local Personal OS",
  collection: "read_later",
  saved_at: "2026-09-11T12:00:00Z",
  tags: ["system", "local"],
  read_status: "unread",
  is_favorite: false,
  reading_time_min: 4,
  scroll_progress: 25,
  hero_image_url: "https://news.ycombinator.com/cover.png",
  note: "Harika bir kisisel isletim sistemi yaklasimi",
  highlights_count: 3,
};

describe("BookmarkCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    harness.mutations = [];
  });

  it("kapak gorseli, alan adi, baslik, okuma suresi ve ozeti render eder", () => {
    const markup = renderToStaticMarkup(
      <BookmarkCard
        bookmark={mockCardBookmark}
        selected={false}
        onToggleSelect={vi.fn()}
        onOpenReader={vi.fn()}
      />,
    );

    expect(markup).toContain("news.ycombinator.com");
    expect(markup).toContain("Show HN: forkOS Local Personal OS");
    expect(markup).toContain("4 dk");
    expect(markup).toContain("Harika bir kisisel isletim sistemi yaklasimi");
    expect(markup).toContain("3 vurgu");
    expect(markup).toContain("#system");
    expect(markup).toContain("#local");
  });

  it("favori degistirme mutasyonunu dogru cagirir", async () => {
    renderToStaticMarkup(
      <BookmarkCard
        bookmark={mockCardBookmark}
        selected={false}
        onToggleSelect={vi.fn()}
        onOpenReader={vi.fn()}
      />,
    );

    const favMutation = harness.mutations.find((m) =>
      m.mutationFn?.toString().includes("favorite"),
    );
    expect(favMutation).toBeDefined();

    await favMutation?.mutationFn?.();
    expect(harness.apiPatch).toHaveBeenCalledWith("/bookmarks/bm-card-1", { favorite: true });

    favMutation?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("bookmark.write");
  });

  it("silme mutasyonunu dogru cagirir", async () => {
    renderToStaticMarkup(
      <BookmarkCard
        bookmark={mockCardBookmark}
        selected={false}
        onToggleSelect={vi.fn()}
        onOpenReader={vi.fn()}
      />,
    );

    const delMutation = harness.mutations.find((m) =>
      m.mutationFn?.toString().includes("del"),
    );
    expect(delMutation).toBeDefined();

    await delMutation?.mutationFn?.();
    expect(harness.apiDel).toHaveBeenCalledWith("/bookmarks/bm-card-1");

    delMutation?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("bookmark.write");
  });
});
