// @vitest-environment jsdom
/**
 * SavedViewPicker — kayıtlı görünüm seçici.
 * Kaydetme, uygulama, sabitleme ve silme akışları mock api ile test edilir;
 * her mutation sonrası views.write invalidation'ı beklenir (kural 14).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ComponentProps } from "react";
import { SavedViewPicker } from "./SavedViewPicker";
import type { SavedViewRow } from "./SavedViewPicker";

vi.mock("@/core/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn() },
  qs: vi.fn(() => ""),
}));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: vi.fn(),
}));

import { api } from "./api";
import { invalidateAfter } from "./invalidation";

const apiGet = vi.mocked(api.get);
const apiPost = vi.mocked(api.post);
const apiPatch = vi.mocked(api.patch);
const apiDel = vi.mocked(api.del);

const views: SavedViewRow[] = [
  {
    id: "v1",
    name: "Okunmamış",
    module: "bookmark",
    filter: { read_status: "unread" },
    sort: null,
    pinned: false,
    position: 2,
  },
  {
    id: "v2",
    name: "Favoriler",
    module: "bookmark",
    filter: { favorite: true },
    sort: null,
    pinned: true,
    position: 0,
  },
];

function renderPicker(props?: Partial<ComponentProps<typeof SavedViewPicker>>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onApply = vi.fn();
  render(
    <QueryClientProvider client={client}>
      <SavedViewPicker
        module="bookmark"
        filters={{ read_status: "unread", q: "" }}
        onApply={onApply}
        {...props}
      />
    </QueryClientProvider>,
  );
  return { onApply };
}

beforeEach(() => {
  apiGet.mockReset();
  apiPost.mockReset();
  apiPatch.mockReset();
  apiDel.mockReset();
  vi.mocked(invalidateAfter).mockReset();
  apiGet.mockResolvedValue(views);
});
afterEach(cleanup);

describe("SavedViewPicker", () => {
  it("kayıtlı görünümleri modülle birlikte çeker", async () => {
    renderPicker();
    await waitFor(() => expect(apiGet).toHaveBeenCalledWith("/views?module=bookmark"));
  });

  it("mevcut filtreyi adla kaydeder ve views.write invalidate eder", async () => {
    apiPost.mockResolvedValue({
      id: "v3",
      name: "Okunmamış",
      module: "bookmark",
      filter: { read_status: "unread" },
      sort: null,
      pinned: false,
      position: 3,
    });
    renderPicker();

    await userEvent.click(await screen.findByRole("button", { name: "Kayıtlı görünümler" }));
    await userEvent.type(screen.getByLabelText("Görünüm adı"), "Okunmamış");
    await userEvent.click(screen.getByRole("button", { name: "Kaydet" }));

    await waitFor(() =>
      expect(apiPost).toHaveBeenCalledWith("/views", {
        name: "Okunmamış",
        module: "bookmark",
        filter: { read_status: "unread" },
      }),
    );
    await waitFor(() => expect(invalidateAfter).toHaveBeenCalledWith("views.write"));
  });

  it("kayıtlı görünüme tıklayınca filtresini uygular", async () => {
    const { onApply } = renderPicker();

    await userEvent.click(await screen.findByRole("button", { name: "Kayıtlı görünümler" }));
    await userEvent.click(await screen.findByRole("button", { name: "Okunmamış" }));

    expect(onApply).toHaveBeenCalledWith({ read_status: "unread" });
  });

  it("yıldızla sabitlemeyi açar/kapatır", async () => {
    renderPicker();

    await userEvent.click(await screen.findByRole("button", { name: "Kayıtlı görünümler" }));
    // v2 sabitli — yıldız "kaldır" der; v1 sabitsiz — "Sabitle" der.
    await userEvent.click(screen.getByRole("button", { name: "Sabitle" }));

    await waitFor(() => expect(apiPatch).toHaveBeenCalledWith("/views/v1", { pinned: true }));
  });

  it("görünümü siler ve views.write invalidate eder", async () => {
    renderPicker();

    await userEvent.click(await screen.findByRole("button", { name: "Kayıtlı görünümler" }));
    await userEvent.click(screen.getByRole("button", { name: '"Okunmamış" görünümünü sil' }));

    await waitFor(() => expect(apiDel).toHaveBeenCalledWith("/views/v1"));
    await waitFor(() => expect(invalidateAfter).toHaveBeenCalledWith("views.write"));
  });
});
