import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Bookmark, BookmarkFullText } from "@/core/types";
import { BookmarkReaderModal } from "./BookmarkReaderModal";

type MutationOptions = {
  mutationFn?: (...args: unknown[]) => unknown;
  onSuccess?: (...args: unknown[]) => void;
};
type QueryOptions = { queryFn: () => unknown; queryKey: readonly unknown[] };

const harness = vi.hoisted(() => ({
  apiDel: vi.fn(),
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  openUri: vi.fn(),
  mutations: [] as MutationOptions[],
  queries: [] as QueryOptions[],
  queryData: {} as Record<string, unknown>,
}));

vi.mock("@/core/api", () => ({
  api: { del: harness.apiDel, get: harness.apiGet, patch: harness.apiPatch, post: harness.apiPost },
  qs: (params: Record<string, string | number | boolean | undefined | null>) => {
    const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
    return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
  },
}));

vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));

vi.mock("@/core/obsidian", () => ({ openObsidianUri: (uri: string) => harness.openUri(uri) }));

vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn((options: MutationOptions) => {
    harness.mutations.push(options);
    return {
      isPending: false,
      mutate: vi.fn((...args: unknown[]) => options.mutationFn?.(...args)),
      mutateAsync: vi.fn((...args: unknown[]) => Promise.resolve(options.mutationFn?.(...args))),
    };
  }),
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    const key = Array.isArray(options.queryKey) ? options.queryKey.join(":") : String(options.queryKey);
    for (const [pattern, val] of Object.entries(harness.queryData)) {
      if (key.includes(pattern)) {
        return { data: val, isLoading: false, isFetching: false, refetch: vi.fn() };
      }
    }
    return { data: undefined, isLoading: false, isFetching: false, refetch: vi.fn() };
  }),
}));

const mockBookmark: Bookmark = {
  id: "bm-pocket-1",
  url: "https://blog.example.com/deep-dive",
  title: "Ajan Mimarisi ve Yerel Sistemler",
  description: "Yerel sistemlerde ajan mimarileri.",
  source: "manual",
  collection: "read_later",
  saved_at: "2026-09-11T10:00:00Z",
  tags: ["mimari", "ai"],
  read_status: "unread",
  favorite: false,
  note: null,
  selection: null,
  reading_time_min: 6,
  word_count: 1200,
  scroll_progress: 35,
  author: "Furkan Turkoglu",
};

const mockFullText: BookmarkFullText = {
  id: "bm-pocket-1",
  title: "Ajan Mimarisi ve Yerel Sistemler",
  url: "https://blog.example.com/deep-dive",
  content_html: "<p>Ajan mimarileri yerel sistemlerde guvenlik ve gizlilik saglar.</p>",
  content_text: "Ajan mimarileri yerel sistemlerde guvenlik ve gizlilik saglar.",
  author: "Furkan Turkoglu",
  reading_time_min: 6,
  word_count: 1200,
  scroll_progress: 35,
  highlights: [
    {
      id: "hl-1",
      bookmark_id: "bm-pocket-1",
      text: "guvenlik ve gizlilik saglar",
      note: "Temel prensip",
      color: "yellow",
      anchor_index: 0,
      created_at: "2026-09-11T10:15:00Z",
    },
  ],
};

describe("BookmarkReaderModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    harness.mutations = [];
    harness.queries = [];
    harness.queryData = {
      fulltext: mockFullText,
    };
  });

  it("kapaliyken veya bookmark yokken hicbir sey render etmez", () => {
    const markupClosed = renderToStaticMarkup(
      <BookmarkReaderModal open={false} bookmark={mockBookmark} onClose={vi.fn()} />,
    );
    expect(markupClosed).toBe("");

    const markupNoBm = renderToStaticMarkup(<BookmarkReaderModal open={true} bookmark={null} onClose={vi.fn()} />);
    expect(markupNoBm).toBe("");
  });

  it("acildiginda baslik, alan adi, sure ve icerigi basariyla render eder", () => {
    const markup = renderToStaticMarkup(<BookmarkReaderModal open={true} bookmark={mockBookmark} onClose={vi.fn()} />);

    expect(markup).toContain("blog.example.com");
    expect(markup).toContain("Ajan Mimarisi ve Yerel Sistemler");
    expect(markup).toContain("Furkan Turkoglu");
    expect(markup).toContain("6 dk okuma");
    expect(markup).toContain("Ajan mimarileri yerel sistemlerde guvenlik ve gizlilik saglar.");
  });

  it("tipografi, font boyutu ve genislik kontrollerini barindirir", () => {
    const markup = renderToStaticMarkup(<BookmarkReaderModal open={true} bookmark={mockBookmark} onClose={vi.fn()} />);

    expect(markup).toContain("Serif");
    expect(markup).toContain("Sans");
    expect(markup).toContain("A-");
    expect(markup).toContain("A+");
    expect(markup).toContain("Genis sutun");
  });

  it("okundu ve favori aksiyonlarini dogru gosterir", () => {
    const markup = renderToStaticMarkup(<BookmarkReaderModal open={true} bookmark={mockBookmark} onClose={vi.fn()} />);

    expect(markup).toContain("Okunmadi");
    expect(markup).toContain("Favoriye ekle");
    expect(markup).toContain("Daha Sonra Oku");
  });

  it("vurgu ekleme mutasyonunu dogru cagirir ve invalidation tetikler", async () => {
    renderToStaticMarkup(<BookmarkReaderModal open={true} bookmark={mockBookmark} onClose={vi.fn()} />);

    const addHighlightMutation = harness.mutations.find((m) => m.mutationFn?.toString().includes("highlights"));
    expect(addHighlightMutation).toBeDefined();

    harness.apiPost.mockResolvedValueOnce({
      id: "hl-new",
      bookmark_id: "bm-pocket-1",
      text: "yeni vurgu",
      color: "yellow",
    });

    await addHighlightMutation?.mutationFn?.({
      text: "yeni vurgu",
      color: "yellow",
      note: "not",
    });

    expect(harness.apiPost).toHaveBeenCalledWith(
      "/bookmarks/bm-pocket-1/highlights",
      expect.objectContaining({
        text: "yeni vurgu",
        color: "yellow",
        anchor_index: 0,
      }),
    );

    addHighlightMutation?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("bookmark.write");
  });

  it("vurguyu flashcarda donusturme mutasyonunu dogru cagirir", async () => {
    renderToStaticMarkup(<BookmarkReaderModal open={true} bookmark={mockBookmark} onClose={vi.fn()} />);

    const convertMutation = harness.mutations.find((m) => m.mutationFn?.toString().includes("convert-to-flashcard"));
    expect(convertMutation).toBeDefined();

    harness.apiPost.mockResolvedValueOnce({ card_id: "card-123" });
    await convertMutation?.mutationFn?.("hl-1");

    expect(harness.apiPost).toHaveBeenCalledWith("/bookmarks/bm-pocket-1/highlights/hl-1/convert-to-flashcard", {});

    convertMutation?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("flashcard.write", "link.write");
  });

  it("literatur notu Vault'ta olusturulur ve Obsidian'da acilir; /notes'a gidilmez", async () => {
    const onClose = vi.fn();
    renderToStaticMarkup(<BookmarkReaderModal open={true} bookmark={mockBookmark} onClose={onClose} />);

    const literatureMutation = harness.mutations.find((m) => m.mutationFn?.toString().includes("source-note"));
    expect(literatureMutation).toBeDefined();

    harness.apiPost.mockResolvedValueOnce({
      forkos_id: "vault-1",
      open_uri: "obsidian://open?vault=f0rknbrain&file=Kaynaklar%2FAjan",
    });
    await literatureMutation?.mutationFn?.();

    expect(harness.apiPost).toHaveBeenCalledWith("/bookmarks/bm-pocket-1/source-note");
    expect(harness.apiPost.mock.calls.some(([path]) => String(path).includes("create-note"))).toBe(false);
    expect(harness.apiPost.mock.calls.some(([path]) => String(path).includes("/notes"))).toBe(false);

    literatureMutation?.onSuccess?.({ open_uri: "obsidian://open?vault=f0rknbrain&file=Kaynaklar%2FAjan" });
    expect(harness.openUri).toHaveBeenCalledWith("obsidian://open?vault=f0rknbrain&file=Kaynaklar%2FAjan");
    expect(harness.invalidate).toHaveBeenCalledWith("obsidian.write");
    expect(harness.invalidate).not.toHaveBeenCalledWith("note.write", "link.write");
    expect(onClose).toHaveBeenCalled();
  });
});
