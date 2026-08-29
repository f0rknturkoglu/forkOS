import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NotesSection } from "./NotesSection";

type MutationOptions = {
  mutationFn?: (variables: never) => Promise<unknown> | unknown;
  onSuccess?: (result: unknown) => void;
};
type QueryOptions = { queryKey: readonly unknown[]; queryFn: () => unknown };

const harness = vi.hoisted(() => ({
  apiDel: vi.fn(),
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  mutations: [] as MutationOptions[],
  queries: [] as QueryOptions[],
}));

vi.mock("@/core/api", () => ({
  api: { del: harness.apiDel, get: harness.apiGet, patch: harness.apiPatch, post: harness.apiPost, upload: vi.fn() },
}));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn((options: MutationOptions) => {
    harness.mutations.push(options);
    return {
      isPending: false,
      mutate: (variables: never) => {
        void options.mutationFn?.(variables);
        options.onSuccess?.({});
      },
    };
  }),
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    return { data: [], isLoading: false };
  }),
}));

describe("NotesSection (Faz 21)", () => {
  beforeEach(() => {
    harness.apiDel.mockReset();
    harness.apiGet.mockReset();
    harness.apiPatch.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.mutations.length = 0;
    harness.queries.length = 0;
  });

  it("listeyi /notes'tan ceker ve bos durum gosterir", () => {
    const markup = renderToStaticMarkup(<NotesSection online />);
    expect(harness.queries[0].queryKey).toEqual(["notes"]);
    expect(markup).toContain("Yerel Notlar");
    expect(markup).toContain("Henüz not yok");
  });

  it("pin gecis PATCH /notes/{id} yapar ve note.write + link.write tazeler", async () => {
    renderToStaticMarkup(<NotesSection online />);

    // Mutation sirasi: create(0), patch(1), archive(2).
    const patch = harness.mutations[1];
    await patch?.mutationFn?.({ id: "note-1", pinned: true } as never);
    expect(harness.apiPatch).toHaveBeenCalledWith("/notes/note-1", { pinned: true });

    patch?.onSuccess?.({});
    expect(harness.invalidate).toHaveBeenCalledWith("note.write", "link.write");
  });

  it("arsiv POST /notes/{id}/archive cagirir", async () => {
    renderToStaticMarkup(<NotesSection online />);
    const archive = harness.mutations[2];
    await archive?.mutationFn?.("note-1" as never);
    expect(harness.apiPost).toHaveBeenCalledWith("/notes/note-1/archive");
  });
});
