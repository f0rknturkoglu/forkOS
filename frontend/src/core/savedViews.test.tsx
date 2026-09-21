// @vitest-environment jsdom
/**
 * Sabitlenmiş görünüm sözleşmesi: `?saved=<id>` derin bağlantısı.
 *
 * Davranış: filtre BİR KEZ uygulanır; bilinmeyen/eski kimlik ve bozuk gövde
 * uygulamayı çökertmez.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useAppliedSavedView, usePinnedSavedViews } from "./savedViews";

const apiGet = vi.fn();

vi.mock("@/core/api", () => ({
  api: { get: (...args: unknown[]) => apiGet(...args), post: vi.fn(), patch: vi.fn(), del: vi.fn() },
  qs: vi.fn(() => ""),
}));

const VIEW = {
  id: "v1",
  name: "Okunmamış",
  module: "media",
  filter: { status: "planned", kind: "book" },
  sort: null,
  pinned: true,
  position: 0,
};

function Probe({
  search,
  apply,
}: {
  search: string;
  apply: (filter: Record<string, unknown>, view: { id: string }) => void;
}) {
  useAppliedSavedView("media", new URLSearchParams(search), apply);
  return null;
}

function renderProbe(search: string) {
  const apply = vi.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <Probe search={search} apply={apply} />
    </QueryClientProvider>,
  );
  return apply;
}

describe("useAppliedSavedView", () => {
  afterEach(() => {
    cleanup();
    apiGet.mockReset();
  });

  it("kayıtlı görünümün filtresini uygular", async () => {
    apiGet.mockResolvedValue([VIEW]);
    const apply = renderProbe("saved=v1");

    await waitFor(() =>
      expect(apply).toHaveBeenCalledWith({ status: "planned", kind: "book" }, expect.objectContaining({ id: "v1" })),
    );
    expect(apply).toHaveBeenCalledTimes(1);
  });

  it("bilinmeyen/eski kimliği sessizce yok sayar", async () => {
    apiGet.mockResolvedValue([VIEW]);
    const apply = renderProbe("saved=eski-id");

    await waitFor(() => expect(apiGet).toHaveBeenCalled());
    expect(apply).not.toHaveBeenCalled();
  });

  it("bozuk gövdede (dizi olmayan yanıt) çökmez", async () => {
    apiGet.mockResolvedValue({ detail: "beklenmeyen" });
    const apply = renderProbe("saved=v1");

    await waitFor(() => expect(apiGet).toHaveBeenCalled());
    expect(apply).not.toHaveBeenCalled();
  });

  it("parametre yoksa hiç sorgu davranışı değişmez ve uygulama olmaz", () => {
    apiGet.mockResolvedValue([VIEW]);
    const apply = renderProbe("");

    expect(apply).not.toHaveBeenCalled();
  });
});

describe("usePinnedSavedViews", () => {
  afterEach(() => {
    cleanup();
    apiGet.mockReset();
  });

  function PinnedProbe() {
    const { data = [] } = usePinnedSavedViews();
    const rows = Array.isArray(data) ? data : [];
    return <output data-testid="pinned">{rows.map((row) => row.name).join(",")}</output>;
  }

  function renderPinned() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <PinnedProbe />
      </QueryClientProvider>,
    );
  }

  it("yalnız sabitlenen görünümleri döndürür", async () => {
    apiGet.mockResolvedValue([VIEW, { ...VIEW, id: "v2", name: "Sabit değil", pinned: false }]);
    renderPinned();

    await waitFor(() => expect(apiGet).toHaveBeenCalledWith("/views"));
    await waitFor(() => expect(document.querySelector("[data-testid=pinned]")?.textContent).toBe("Okunmamış"));
  });

  it("bozuk gövdeyi boş liste sayar (sidebar çökmez)", async () => {
    apiGet.mockResolvedValue({ detail: "bozuk" });
    renderPinned();

    await waitFor(() => expect(document.querySelector("[data-testid=pinned]")?.textContent).toBe(""));
  });
});
