// @vitest-environment jsdom
/**
 * Home kartları: Son tarihler + Kariyer (P2 §22/§23/§24).
 *
 * İki kart aynı sorunun farklı yarısını yanıtlar ve BİRBİRİNİ TEKRAR ETMEZ:
 * kariyer son tarihleri yalnız Kariyer kartında (bağlamıyla), kalan tarihler
 * Son tarihler kartında görünür. Satır hedefi yoksa satır bağlantı GİBİ
 * görünmez; liste sınırlıdır ve fazlası sayıyla bildirilir.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { hydrateEntityRegistry } from "@/core/entityRegistry";
import { DeadlinesWidget } from "./DeadlinesWidget";
import { CareerWidget } from "./CareerWidget";

const apiGet = vi.fn();

vi.mock("@/core/api", () => ({
  api: { get: (...args: unknown[]) => apiGet(...args) },
  qs: vi.fn(() => ""),
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
  type: "todo",
  title: "Vergi beyanı",
  due_at: iso(2),
  module: "todo",
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
  title: "Görüşme yaklaşıyor",
  body: null,
  entity_id: "opp-1",
  entity_type: "opportunity",
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

function renderWidget(widget: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{widget}</QueryClientProvider>);
}

const EMPTY = { "/deadlines": [], "/opportunities/followups": [], "/notifications": [] };

beforeEach(() => {
  apiGet.mockReset();
  hydrateEntityRegistry([
    {
      type: "todo",
      label: "Görev",
      label_plural: "Görevler",
      route: "/todos?focus={id}",
      icon: "Check",
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
});

afterEach(() => {
  cleanup();
  hydrateEntityRegistry([]);
});

describe("Son tarihler kartı", () => {
  it("kayıt yoksa hiç çizilmez", async () => {
    serve(EMPTY);
    const { container } = renderWidget(<DeadlinesWidget />);
    await waitFor(() => expect(apiGet).toHaveBeenCalledWith("/deadlines"));
    expect(container.textContent).toBe("");
  });

  it("yaklaşan tarihleri sırayla gösterir ve kaydın rotasına bağlar", async () => {
    serve({
      ...EMPTY,
      "/deadlines": [deadline({ due_at: iso(3), title: "Uzak tarih" }), deadline({ title: "Yakın tarih" })],
    });
    renderWidget(<DeadlinesWidget />);

    expect(await screen.findByText("Yakın tarih")).toBeTruthy();
    expect(screen.getByText("2 gün kaldı · Görev")).toBeTruthy();
    const link = screen.getByRole("link", { name: /Yakın tarih/ });
    expect(link.getAttribute("href")).toBe("#/todos?focus=e1");
  });

  it("kariyer son tarihlerini burada tekrarlamaz", async () => {
    serve({
      ...EMPTY,
      "/deadlines": [
        deadline({ entity_id: "opp-1", type: "opportunity", module: "opportunity", title: "Başvuru son günü" }),
        deadline(),
      ],
    });
    renderWidget(<DeadlinesWidget />);

    expect(await screen.findByText("Vergi beyanı")).toBeTruthy();
    expect(screen.queryByText("Başvuru son günü")).toBeNull();
  });

  it("tanınmayan kayıt tipini bağlantı gibi göstermez", async () => {
    serve({ ...EMPTY, "/deadlines": [deadline({ type: "gizemli", title: "Bilinmeyen kayıt" })] });
    renderWidget(<DeadlinesWidget />);

    expect(await screen.findByText("Bilinmeyen kayıt")).toBeTruthy();
    expect(screen.queryByRole("link", { name: /Bilinmeyen kayıt/ })).toBeNull();
  });

  it("listeyi sınırlar ve fazlasını sayıyla bildirir", async () => {
    serve({
      ...EMPTY,
      "/deadlines": Array.from({ length: 6 }, (_, index) =>
        deadline({ entity_id: `e${index}`, title: `Tarih ${index + 1}`, due_at: iso(index + 1) }),
      ),
    });
    renderWidget(<DeadlinesWidget />);

    await screen.findByText("Tarih 1");
    expect(screen.getAllByText(/^Tarih \d$/)).toHaveLength(5);
    expect(screen.getByText("1 kayıt daha var.")).toBeTruthy();
  });
});

describe("Kariyer kartı", () => {
  it("kariyer verisi yoksa hiç çizilmez", async () => {
    serve(EMPTY);
    const { container } = renderWidget(<CareerWidget />);
    await waitFor(() => expect(apiGet).toHaveBeenCalledWith("/opportunities/followups"));
    expect(container.textContent).toBe("");
  });

  it("takip, kariyer bildirimi ve kariyer son tarihini tek listede toplar", async () => {
    serve({
      ...EMPTY,
      "/opportunities/followups": [followup()],
      "/notifications": [notification({ id: 9, entity_id: null, kind: "opportunity.digest", title: "5 yeni fırsat" })],
      "/deadlines": [
        deadline({
          entity_id: "opp-2",
          type: "opportunity",
          module: "opportunity",
          title: "Mülakat günü",
          due_at: iso(0),
        }),
      ],
    });
    renderWidget(<CareerWidget />);

    expect(await screen.findByText("Company X takibi")).toBeTruthy();
    expect(screen.getByText("Yarın · Takip")).toBeTruthy();
    expect(screen.getByText("Mülakat günü")).toBeTruthy();
    expect(screen.getByText("Bugün · Son tarih")).toBeTruthy();
    expect(screen.getByText("5 yeni fırsat")).toBeTruthy();
    // Kaydı olmayan satır Kariyer yüzeyine gider: "tümü" hedefi.
    expect(screen.getByRole("link", { name: /5 yeni fırsat/ }).getAttribute("href")).toBe("#/opportunities");
    expect(screen.getByRole("link", { name: /tümü/ }).getAttribute("href")).toBe("#/opportunities");
  });

  it("genel bildirimleri ve okunmuşları kariyer kartına almaz", async () => {
    serve({
      ...EMPTY,
      "/notifications": [
        notification({ id: 1, entity_type: "project", entity_id: "p1", title: "RepoLens hareketsiz" }),
        notification({ id: 2, title: "Okunmuş kariyer bildirimi", read_at: iso(0, 7) }),
      ],
    });
    const { container } = renderWidget(<CareerWidget />);

    await waitFor(() => expect(apiGet).toHaveBeenCalledWith("/notifications"));
    expect(container.textContent).toBe("");
  });

  it("aynı kaydın bildirimini son tarihle birlikte tekrar göstermez", async () => {
    serve({
      ...EMPTY,
      "/deadlines": [deadline({ entity_id: "opp-3", type: "opportunity", module: "opportunity", title: "Son gün" })],
      "/notifications": [notification({ id: 3, entity_id: "opp-3", title: "Son gün bildirimi" })],
    });
    renderWidget(<CareerWidget />);

    expect(await screen.findByText("Son gün")).toBeTruthy();
    await waitFor(() => expect(screen.queryByText("Son gün bildirimi")).toBeNull());
  });
});
