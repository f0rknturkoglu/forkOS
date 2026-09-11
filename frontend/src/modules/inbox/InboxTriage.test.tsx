import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Bookmark } from "@/core/types";
import { InboxTodayWidget } from "./InboxTodayWidget";
import { InboxFocusTriageModal } from "./InboxFocusTriageModal";

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
  mutations: [] as MutationOptions[],
  queries: [] as QueryOptions[],
  queryData: {} as Record<string, unknown>,
}));

vi.mock("@/app/router", () => ({
  useHashRoute: () => ({ path: "/today", params: new URLSearchParams() }),
  navigate: vi.fn(),
}));

vi.mock("@/core/api", () => ({
  api: { del: harness.apiDel, get: harness.apiGet, patch: harness.apiPatch, post: harness.apiPost },
  qs: (params: Record<string, string | number | boolean | undefined | null>) => {
    const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
    return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
  },
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
    return { isPending: false, mutate: vi.fn() };
  }),
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    const key = Array.isArray(options.queryKey) ? options.queryKey.join(":") : String(options.queryKey);
    for (const [pattern, val] of Object.entries(harness.queryData)) {
      if (key.includes(pattern)) {
        return { data: val, isLoading: false, refetch: vi.fn() };
      }
    }
    return { data: [], isLoading: false, refetch: vi.fn() };
  }),
}));

const sampleBookmarks: Bookmark[] = [
  {
    id: "bm-1",
    url: "https://example.com/article-1",
    title: "Ornek Makale 1",
    description: null,
    note: "Onemli mimari notu burada.",
    selection: "Alintilanan cumle",
    collection: "inbox",
    read_status: "unread",
    favorite: false,
    saved_at: "2026-09-10T10:00:00Z",
    source: "extension",
    tags: ["mimari", "sistem"],
    is_duplicate: false,
  },
  {
    id: "bm-2",
    url: "https://docs.example.org/guide",
    title: "Rehber Dokumani",
    description: null,
    note: null,
    selection: null,
    collection: "inbox",
    read_status: "unread",
    favorite: false,
    saved_at: "2026-09-11T09:00:00Z",
    source: "manual",
    tags: [],
    is_duplicate: true,
    existing_collection: "reference",
  },
];

describe("InboxTodayWidget", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.mutations.length = 0;
    harness.queries.length = 0;
    harness.queryData = {};
  });

  it("bos durumda sakin mesaj gosterir", () => {
    harness.queryData["bookmarks"] = [];
    const html = renderToStaticMarkup(<InboxTodayWidget />);
    expect(html).toContain("Gelen kutusu temiz. Bekleyen kayit yok.");
    expect(html).toContain("Gelen Kutusu");
  });

  it("kayitlar oldugunda basliklari, notlari ve hizli aksiyonlari render eder", () => {
    harness.queryData["bookmarks"] = sampleBookmarks;
    const html = renderToStaticMarkup(<InboxTodayWidget />);
    expect(html).toContain("Ornek Makale 1");
    expect(html).toContain("Rehber Dokumani");
    expect(html).toContain("Not var");
    expect(html).toContain("Tumunu Ayikla (Triage Modu)");
    expect(html).toContain("Arsivle");
    expect(html).toContain("Goreve donustur");
    expect(html).toContain("Sonra oku");
  });

  it("hicbir emoji icermez", () => {
    harness.queryData["bookmarks"] = sampleBookmarks;
    const html = renderToStaticMarkup(<InboxTodayWidget />);
    const emojiRegex = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u;
    expect(emojiRegex.test(html)).toBe(false);
  });
});

describe("InboxFocusTriageModal", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.mutations.length = 0;
    harness.queries.length = 0;
    harness.queryData = {};
  });

  it("kapaliyken hicbir sey render etmez", () => {
    const html = renderToStaticMarkup(<InboxFocusTriageModal open={false} onClose={() => {}} />);
    expect(html).toBe("");
  });

  it("acikken odaklanilan kaydi, klavye kisayollarini ve notu render eder", () => {
    harness.queryData["triage-modal"] = sampleBookmarks;
    const html = renderToStaticMarkup(<InboxFocusTriageModal open={true} onClose={() => {}} />);
    expect(html).toContain("Ornek Makale 1");
    expect(html).toContain("example.com");
    expect(html).toContain("Onemli mimari notu burada.");
    expect(html).toContain("Alintilanan cumle");
    expect(html).toContain("1 / 2");
    expect(html).toContain("Arsivle");
    expect(html).toContain("Gorev Yap");
    expect(html).toContain("Not Olustur");
    expect(html).toContain("Ogrenme");
    expect(html).toContain("Projeler");
    expect(html).toContain("Cope At (D)");
  });

  it("mukerrer kayit rozetini dogru gosterir", () => {
    harness.queryData["triage-modal"] = [sampleBookmarks[1]];
    const html = renderToStaticMarkup(<InboxFocusTriageModal open={true} onClose={() => {}} />);
    expect(html).toContain("Zaten kayitli: reference");
  });

  it("hicbir emoji icermez", () => {
    harness.queryData["triage-modal"] = sampleBookmarks;
    const html = renderToStaticMarkup(<InboxFocusTriageModal open={true} onClose={() => {}} />);
    const emojiRegex = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u;
    expect(emojiRegex.test(html)).toBe(false);
  });
});
