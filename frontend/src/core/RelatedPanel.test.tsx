// @vitest-environment jsdom
/**
 * RelatedPanel — çekirdek bağ altyapısının ekran yüzü (Faz 3 kabul kriteri).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { hydrateEntityRegistry } from "./entityRegistry";
import { RelatedPanel } from "./RelatedPanel";
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
  useDebounced: (value: string) => value,
}));

import { api } from "./api";

const apiGet = vi.mocked(api.get);
const apiPost = vi.mocked(api.post);
const apiDel = vi.mocked(api.del);

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <RelatedPanel entityId="opp-1" />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  hydrateEntityRegistry([
    {
      type: "bookmark",
      label: "Yer imi",
      label_plural: "Yer imleri",
      route: "/bookmarks?focus={id}",
      icon: "Bookmark",
      searchable: true,
      linkable: true,
    },
    {
      type: "opportunity",
      label: "Fırsat",
      label_plural: "Fırsatlar",
      route: "/opportunities?focus={id}",
      icon: "Target",
      searchable: true,
      linkable: true,
    },
  ]);
  apiGet.mockReset();
  apiPost.mockReset();
  apiDel.mockReset();
});
afterEach(cleanup);

describe("RelatedPanel", () => {
  it("ilişkili kayıtları ilişki etiketine göre listeler ve rotaya bağlar", async () => {
    apiGet.mockImplementation(async (path: string) => {
      if (path === "/entities/opp-1/related") {
        return [
          {
            relation: "saved_from",
            direction: "incoming",
            label: "Buradan kaydedildi",
            entity: { id: "bm-1", type: "bookmark", title: "İlan sayfası", updated_at: "2026-08-26T10:00:00Z" },
          },
        ];
      }
      return {};
    });

    renderPanel();
    expect(await screen.findByText("İlan sayfası")).toBeTruthy();
    expect(screen.getByText("Buradan kaydedildi")).toBeTruthy();
    // Kayıt defterindeki rotaya giden link.
    const link = screen.getByRole("link", { name: /İlan sayfası/ });
    expect(link.getAttribute("href")).toBe("#/bookmarks?focus=bm-1");
  });

  it("bağ kaldırma DELETE /links çağırır ve tazeler", async () => {
    apiGet.mockImplementation(async (path: string) =>
      path === "/entities/opp-1/related"
        ? [
            {
              relation: "saved_from",
              direction: "incoming",
              label: "Buradan kaydedildi",
              entity: { id: "bm-1", type: "bookmark", title: "İlan sayfası", updated_at: "2026-08-26T10:00:00Z" },
            },
          ]
        : {},
    );
    apiDel.mockResolvedValue(undefined as never);

    renderPanel();
    await screen.findByText("İlan sayfası");
    const unlink = screen.getByRole("button", { name: "Bağı kaldır" });
    fireEvent.click(unlink);

    await waitFor(() =>
      expect(apiDel).toHaveBeenCalledWith("/links", { from_id: "opp-1", to_id: "bm-1", relation: "saved_from" }),
    );
  });

  it("'Bağla' arama panelini açar ve seçilen kaydı bağlar", async () => {
    apiGet.mockImplementation(async (path: string) => (path.startsWith("/entities/") ? [] : {}));
    apiPost.mockResolvedValue({ ok: true } as never);

    renderPanel();
    fireEvent.click(screen.getByRole("button", { name: /Bağla/ }));
    expect(await screen.findByPlaceholderText("Kayıt ara…")).toBeTruthy();

    // Arama: 2 karakter girince /search çağrılır, sonuç tıklanınca link kurulur.
    apiGet.mockImplementation(async (path: string) => {
      if (path.startsWith("/entities/")) return [];
      if (path.startsWith("/search")) {
        return { "Yer imleri": [{ id: "bm-2", type: "bookmark", title: "Bağlanacak kayıt" }] };
      }
      return {};
    });
    const input = screen.getByPlaceholderText("Kayıt ara…");
    fireEvent.change(input, { target: { value: "bağla" } });

    const candidate = await screen.findByText("Bağlanacak kayıt");
    fireEvent.click(candidate);

    await waitFor(() =>
      expect(apiPost).toHaveBeenCalledWith("/links", { from_id: "opp-1", to_id: "bm-2", relation: "related" }),
    );
  });
});
