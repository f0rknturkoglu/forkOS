// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { todayKey } from "@/lib/date";
import { FinancePage } from "./FinancePage";

vi.mock("@/core/api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn() } }));
vi.mock("@/app/router", () => ({ useHashRoute: () => ({ params: new URLSearchParams() }) }));
vi.mock("@/core/dialog", () => ({ confirmDialog: vi.fn(async () => true), DialogHost: () => null }));
import { api } from "@/core/api";

const apiGet = vi.mocked(api.get);
const apiPost = vi.mocked(api.post);
const recurring = [
  {
    id: "r1",
    title: "Netflix",
    amount: "99.90",
    currency: "TRY",
    category: "subscriptions",
    billing_day: 1,
    frequency: "monthly",
    next_due_at: todayKey(),
    active: true,
    note: null,
    sub: "netflix",
  },
  {
    id: "r2",
    title: "Cloud",
    amount: "10",
    currency: "USD",
    category: "subscriptions",
    billing_day: 1,
    frequency: "monthly",
    next_due_at: todayKey(),
    active: true,
    note: null,
    sub: null,
  },
];

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <ToastProvider>
        <FinancePage />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiGet.mockReset().mockImplementation(async (path: string) => (path === "/recurring-payments" ? recurring : []));
  apiPost.mockReset().mockResolvedValue({});
});
afterEach(cleanup);

it("abonelikleri ve yaklaşan ödemeleri gösterir; eski finans yüzeyi için veri çekmez", async () => {
  renderPage();
  expect((await screen.findAllByText("Netflix")).length).toBeGreaterThan(0);
  expect(screen.getAllByText("Netflix").length).toBeGreaterThan(0);
  expect(screen.getByText("Aylık sabit yük")).toBeTruthy();
  expect(screen.queryByText("Net durum")).toBeNull();
  expect(apiGet.mock.calls.map(([path]) => path).sort()).toEqual([
    "/recurring-payments",
    "/recurring-payments/history",
  ]);
});

it("para birimine göre yalnız ilgili abonelikleri gösterir", async () => {
  renderPage();
  await screen.findAllByText("Netflix");
  fireEvent.click(screen.getByRole("button", { name: "USD" }));
  expect(screen.getAllByText("Cloud").length).toBeGreaterThan(0);
  expect(screen.queryByText("Netflix")).toBeNull();
});

it("yeni kayıt akışı abonelik türüyle açılır ve ödeme eylemi korunur", async () => {
  renderPage();
  await screen.findAllByText("Netflix");
  fireEvent.click(screen.getByRole("button", { name: /Abonelik ekle/ }));
  const dialog = await screen.findByRole("dialog", { name: "Yeni ekle" });
  expect(within(dialog).getAllByText("Abonelik").length).toBeGreaterThan(0);
  fireEvent.click(within(dialog).getByRole("button", { name: "Vazgeç" }));
  fireEvent.click(screen.getByRole("button", { name: "Ödendi" }));
  await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/recurring-payments/r1/pay"));
});

it("ödendi geçmişi yalnız abonelik ödeme kanıtını gösterir", async () => {
  apiGet.mockImplementation(async (path: string) =>
    path === "/recurring-payments"
      ? recurring
      : path === "/recurring-payments/history"
        ? [{ id: 7, title: "Eski ödeme", paid_at: "2026-09-10T12:00:00Z" }]
        : [],
  );
  renderPage();
  expect(await screen.findByText("Eski ödeme")).toBeTruthy();
  expect(screen.getByText("Ödendi / Geçmiş")).toBeTruthy();
});
