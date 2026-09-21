// @vitest-environment jsdom
/**
 * Dikkat yüzeyi sözleşmesi (P2 §23/§70).
 *
 * Tek yüzey, sınırlı satır, dürüst kısmi veri. Bir ucun düşmesi Home'u
 * çökertmez; hiçbir uç veri vermezse yüzey hiç çizilmez (sessizlik başarıdır).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AttentionWidget } from "./AttentionWidget";

const apiGet = vi.fn();

vi.mock("@/core/api", () => ({
  api: { get: (...args: unknown[]) => apiGet(...args) },
  qs: vi.fn(() => ""),
}));

vi.mock("@/core/entityRegistry", () => ({
  entityRoute: (type: string, id: string) => `#/entity/${type}/${id}`,
}));

const now = new Date();
const iso = (offsetDays: number, hours = 9) => {
  const date = new Date(now);
  date.setDate(date.getDate() + offsetDays);
  date.setHours(hours, 0, 0, 0);
  return date.toISOString();
};

const deadline = (overrides: Record<string, unknown> = {}) => ({
  entity_id: "e1",
  type: "opportunity",
  title: "ALES başvurusu",
  due_at: iso(2),
  module: "opportunity",
  sub_kind: null,
  priority: 1,
  ...overrides,
});

const followup = (overrides: Record<string, unknown> = {}) => ({
  id: "f1",
  title: "Company X takibi",
  status: "applied",
  follow_up_at: iso(1),
  note: null,
  ...overrides,
});

const notification = (overrides: Record<string, unknown> = {}) => ({
  id: 7,
  kind: "proactivity",
  title: "RepoLens hareketsiz",
  body: "21 gündür hareket yok",
  entity_id: "p9",
  entity_type: "project",
  importance: 2,
  created_at: iso(0, 8),
  read_at: null,
  ...overrides,
});

/** Uç bazlı sahte yanıt: yol → gövde | Error (tanımsız uç boş liste sayılır). */
function serve(routes: Record<string, unknown>) {
  apiGet.mockImplementation((path: string) => {
    const value = routes[path];
    if (value instanceof Error) return Promise.reject(value);
    return Promise.resolve(value ?? []);
  });
}

function renderWidget() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AttentionWidget />
    </QueryClientProvider>,
  );
}

const EMPTY_ROUTES = {
  "/deadlines": [],
  "/opportunities/followups": [],
  "/notifications": [],
};

describe("AttentionWidget", () => {
  beforeEach(() => apiGet.mockReset());
  afterEach(cleanup);

  it("hiçbir kaynak veri vermezse hiçbir şey çizmez", async () => {
    serve(EMPTY_ROUTES);
    const { container } = renderWidget();

    await waitFor(() => expect(apiGet).toHaveBeenCalledWith("/deadlines"));
    await waitFor(() => expect(container.textContent).toBe(""));
  });

  it("yalnız son tarih varsa tek satır gösterir", async () => {
    serve({ ...EMPTY_ROUTES, "/deadlines": [deadline()] });
    renderWidget();

    expect(await screen.findByText("ALES başvurusu")).toBeTruthy();
    expect(screen.getByText("T-2")).toBeTruthy();
    expect(screen.queryByText("Company X takibi")).toBeNull();
  });

  it("yalnız takip varsa zamanını dürüstçe yazar", async () => {
    serve({ ...EMPTY_ROUTES, "/opportunities/followups": [followup()] });
    renderWidget();

    expect(await screen.findByText("Company X takibi")).toBeTruthy();
    expect(screen.getByText("Yarın")).toBeTruthy();
  });

  it("okunmuş bildirimi göstermez", async () => {
    serve({
      ...EMPTY_ROUTES,
      "/notifications": [notification(), notification({ id: 8, title: "Okunmuş", read_at: iso(0, 7) })],
    });
    renderWidget();

    expect(await screen.findByText("RepoLens hareketsiz")).toBeTruthy();
    expect(screen.queryByText("Okunmuş")).toBeNull();
  });

  it("aynı kaydın bildirim tekrarını göstermez (anlamsal tekrar)", async () => {
    serve({
      ...EMPTY_ROUTES,
      "/deadlines": [deadline({ entity_id: "p9", title: "RepoLens son tarihi" })],
      "/notifications": [notification({ entity_id: "p9", title: "RepoLens hareketsiz" })],
    });
    renderWidget();

    expect(await screen.findByText("RepoLens son tarihi")).toBeTruthy();
    await waitFor(() => expect(screen.queryByText("RepoLens hareketsiz")).toBeNull());
  });

  it("satır sayısını sınırlar ve fazlasını sayıyla bildirir", async () => {
    serve({
      ...EMPTY_ROUTES,
      "/deadlines": Array.from({ length: 5 }, (_, index) =>
        deadline({ entity_id: `e${index}`, title: `Son tarih ${index + 1}`, due_at: iso(index + 1) }),
      ),
      "/notifications": [notification(), notification({ id: 9, title: "Ek bildirim" })],
    });
    renderWidget();

    await screen.findByText("Son tarih 1");
    const rows = screen.getAllByText(/Son tarih|Ek bildirim|RepoLens/);
    expect(rows.length).toBe(5);
    expect(screen.getByText("2 kayıt daha var.")).toBeTruthy();
  });

  it("kısmi uç hatasında kalan veriyi gösterir ve dürüst uyarı verir", async () => {
    serve({
      ...EMPTY_ROUTES,
      "/deadlines": [deadline()],
      "/notifications": new Error("503"),
    });
    renderWidget();

    expect(await screen.findByText("ALES başvurusu")).toBeTruthy();
    expect(screen.getByText(/Bazı kaynaklara ulaşılamadı/)).toBeTruthy();
  });

  it("tüm uçlar hata verirse (çevrimdışı) boş kalır ve çökmez", async () => {
    serve({
      "/deadlines": new Error("offline"),
      "/opportunities/followups": new Error("offline"),
      "/notifications": new Error("offline"),
    });
    const { container } = renderWidget();

    await waitFor(() => expect(apiGet).toHaveBeenCalledWith("/deadlines"));
    await waitFor(() => expect(container.textContent).toBe(""));
  });

  it("satırlar kaydın kendi rotasına gider", async () => {
    serve({ ...EMPTY_ROUTES, "/deadlines": [deadline()] });
    renderWidget();

    const link = await screen.findByRole("link", { name: /ALES başvurusu/ });
    expect(link.getAttribute("href")).toBe("#/entity/opportunity/e1");
  });
});
