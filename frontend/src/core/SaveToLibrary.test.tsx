// @vitest-environment jsdom
/**
 * SaveToLibrary — her yerden yer imi kaydetme akışı (Faz 4 kabul kriteri).
 * capture + (entity varsa) saved_from link'i + nereye gittiğini söyleyen toast.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSaveToLibrary } from "./SaveToLibrary";
import { ToastProvider } from "./ui";

vi.mock("@/core/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    del: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
  },
  qs: vi.fn(() => ""),
}));
vi.mock("@/lib/hooks", () => ({
  useOnline: () => true,
}));

import { api } from "./api";

const apiPost = vi.mocked(api.post);

function Host({ url, title, entityId }: { url: string; title: string; entityId?: string }) {
  const { save } = useSaveToLibrary();
  return (
    <button type="button" onClick={() => save({ url, title, collection: "reference", entity_id: entityId })}>
      kaydet
    </button>
  );
}

function renderHost(props: { url: string; title: string; entityId?: string }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <Host {...props} />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiPost.mockReset();
});
afterEach(cleanup);

describe("useSaveToLibrary", () => {
  it("capture çağırır ve hedef koleksiyonu toast'ta söyler", async () => {
    apiPost.mockImplementation(async (path: string) => {
      if (path === "/capture") return { id: "bm-1", duplicate: false, collection: "reference" };
      return { ok: true };
    });

    renderHost({ url: "https://example.com/ilan", title: "Örnek ilan" });
    await userEvent.click(screen.getByRole("button", { name: "kaydet" }));

    await waitFor(() => {
      const captureCall = apiPost.mock.calls.find(([p]) => p === "/capture");
      expect(captureCall).toBeTruthy();
      const body = captureCall![1] as { url: string; title: string; collection: string; client_uuid: string };
      expect(body.url).toBe("https://example.com/ilan");
      expect(body.collection).toBe("reference");
      expect(body.client_uuid).toBeTruthy();
    });
    expect(await screen.findByText(/Kaynak eklendi/)).toBeTruthy();
  });

  it("entity_id verilirse saved_from link'ini kurar (bookmark -> entity)", async () => {
    apiPost.mockImplementation(async (path: string) => {
      if (path === "/capture") return { id: "bm-1", duplicate: false, collection: "reference" };
      if (path === "/links") return { ok: true };
      return { ok: true };
    });

    renderHost({ url: "https://example.com/ilan", title: "Örnek ilan", entityId: "opp-1" });
    await userEvent.click(screen.getByRole("button", { name: "kaydet" }));

    await waitFor(() =>
      expect(apiPost).toHaveBeenCalledWith("/links", { from_id: "bm-1", to_id: "opp-1", relation: "saved_from" }),
    );
  });

  it("toast 'Aç' aksiyonu yer iminde açar", async () => {
    apiPost.mockImplementation(async (path: string) => {
      if (path === "/capture") return { id: "bm-7", duplicate: false, collection: "reference" };
      return { ok: true };
    });

    renderHost({ url: "https://example.com/x", title: "Açılacak kayıt" });
    await userEvent.click(screen.getByRole("button", { name: "kaydet" }));

    const open = await screen.findByRole("button", { name: "Aç" });
    await userEvent.click(open);
    expect(window.location.hash).toBe("#/bookmarks?focus=bm-7");
  });
});
