import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FinancePage } from "./FinancePage";

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
  stateCursor: 0,
  stateValues: [] as unknown[],
}));

vi.mock("react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react")>();
  return {
    ...actual,
    useState: (initial: unknown | (() => unknown)) => {
      const index = harness.stateCursor++;
      if (!(index in harness.stateValues)) {
        harness.stateValues[index] = typeof initial === "function" ? initial() : initial;
      }
      return [
        harness.stateValues[index],
        (value: unknown) => {
          harness.stateValues[index] = value;
        },
      ];
    },
  };
});
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
    const key = String(options.queryKey[0]);
    return { data: key in harness.queryData ? harness.queryData[key] : undefined, isLoading: false };
  }),
}));

const expenses = [
  {
    id: "e1",
    title: "Market",
    amount: "150.5",
    currency: "TRY",
    category: "food",
    spent_on: "2026-08-26",
    note: null,
    sub: null,
  },
];
const recurring = [
  {
    id: "r1",
    title: "Netflix",
    amount: "99.9",
    currency: "TRY",
    category: "subscriptions",
    billing_day: null,
    frequency: "monthly",
    next_due_at: "2026-09-01",
    active: true,
    note: null,
    sub: "wow",
  },
];

describe("finance flow", () => {
  beforeEach(() => {
    harness.apiDel.mockReset();
    harness.apiGet.mockReset();
    harness.apiPatch.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.mutations.length = 0;
    harness.queries.length = 0;
    harness.queryData = {};
    harness.stateCursor = 0;
    harness.stateValues = [];
  });

  it("lists expenses and recurring payments from their queries", async () => {
    harness.queryData = { expenses, recurring };
    harness.stateValues = ["expenses", "", "", "other", ""];
    const markup = renderToStaticMarkup(<FinancePage />);

    expect(markup).toContain("Market");
    expect(markup).toContain("150,5"); // tr-TR sayi bicimi

    harness.stateCursor = 0;
    harness.stateValues = ["recurring", "", "", "other", ""];
    const recurringMarkup = renderToStaticMarkup(<FinancePage />);
    expect(recurringMarkup).toContain("Netflix");
    expect(recurringMarkup).toContain("Ödendi");

    const expensesQuery = harness.queries.find((query) => query.queryKey[0] === "expenses");
    const recurringQuery = harness.queries.find((query) => query.queryKey[0] === "recurring");
    const summaryQuery = harness.queries.find((query) => query.queryKey[0] === "expense-summary");
    await expensesQuery?.queryFn();
    await recurringQuery?.queryFn();
    await summaryQuery?.queryFn();
    expect(harness.apiGet).toHaveBeenCalledWith("/expenses");
    expect(harness.apiGet).toHaveBeenCalledWith("/recurring-payments");
    expect(harness.apiGet).toHaveBeenCalledWith("/expenses/summary");
  });

  it("creates an expense in the expenses tab with the right payload and finance.write invalidation", () => {
    harness.stateValues = ["expenses", "Market", "150.5", "food", ""];
    renderToStaticMarkup(<FinancePage />);

    const create = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.();
      return harness.apiPost.mock.calls.some(([url]) => url === "/expenses");
    });
    expect(create).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/expenses", {
      title: "Market",
      amount: "150.5",
      category: "food",
      sub: null,
    });
    create?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("finance.write");
  });

  it("marks a recurring payment as paid and deletes an expense via the right endpoints", () => {
    harness.stateValues = ["recurring", "", "", "other", ""];
    renderToStaticMarkup(<FinancePage />);

    const pay = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.("r1");
      return harness.apiPost.mock.calls.some(([url]) => url === "/recurring-payments/r1/pay");
    });
    expect(pay).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/recurring-payments/r1/pay");
    pay?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("finance.write");

    harness.invalidate.mockClear();
    const remove = harness.mutations.find((mutation) => {
      harness.apiDel.mockClear();
      mutation.mutationFn?.({ id: "e1", kind: "expenses" });
      return harness.apiDel.mock.calls.some(([url]) => url === "/expenses/e1");
    });
    expect(remove).toBeDefined();
    expect(harness.apiDel).toHaveBeenCalledWith("/expenses/e1");
    remove?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("finance.write");
  });
});
