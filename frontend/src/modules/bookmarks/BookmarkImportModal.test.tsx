import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BookmarkImportModal } from "./BookmarkImportModal";

type MutationOptions = {
  mutationFn?: (...args: unknown[]) => unknown;
  onSuccess?: (...args: unknown[]) => void;
};

const harness = vi.hoisted(() => ({
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  mutations: [] as MutationOptions[],
}));

vi.mock("@/core/api", () => ({
  api: { post: harness.apiPost },
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

describe("BookmarkImportModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    harness.mutations = [];
  });

  it("kapaliyken render edilmez", () => {
    const markup = renderToStaticMarkup(
      <BookmarkImportModal open={false} onClose={vi.fn()} />,
    );
    expect(markup).toBe("");
  });

  it("acildiginda baslik, dosya secici ve koleksiyon secicisini render eder", () => {
    const markup = renderToStaticMarkup(
      <BookmarkImportModal open={true} onClose={vi.fn()} />,
    );

    expect(markup).toContain("Yer Imlerini Ice Aktar");
    expect(markup).toContain("Netscape HTML (Chrome, Firefox, Safari)");
    expect(markup).toContain("Hedef Koleksiyon");
    expect(markup).toContain("Daha Sonra Oku");
    expect(markup).toContain("Gelen Kutusu");
  });

  it("ice aktarma mutasyonunu dogru cagirir ve invalidation tetikler", async () => {
    renderToStaticMarkup(
      <BookmarkImportModal open={true} onClose={vi.fn()} />,
    );

    const importMutation = harness.mutations.find((m) =>
      m.mutationFn?.toString().includes("/bookmarks/import"),
    );
    expect(importMutation).toBeDefined();

    harness.apiPost.mockResolvedValueOnce({ imported: 42 });
    await importMutation?.mutationFn?.();

    expect(harness.apiPost).toHaveBeenCalledWith("/bookmarks/import", expect.any(Object));

    importMutation?.onSuccess?.({ imported: 42 });
    expect(harness.invalidate).toHaveBeenCalledWith("bookmark.write");
  });
});
