import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { todayKey } from "@/lib/date";
import { FinancePage } from "./FinancePage";

type MutationOptions = { mutationFn?: (...args: unknown[]) => unknown; onSuccess?: (...args: unknown[]) => void };
type QueryOptions = { queryFn: () => unknown; queryKey: readonly unknown[] };

const harness = vi.hoisted(() => ({
  apiDel: vi.fn(),
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  navigate: vi.fn(),
  mutations: [] as MutationOptions[],
  queries: [] as QueryOptions[],
  queryData: {} as Record<string, unknown>,
  routeParams: "",
  stateCursor: 0,
  stateValues: [] as unknown[],
}));

// Form alanlari yerel state'te yasar; SSR anlik goruntusunde onlari surmek icin
// useState cursor'lu bir kosum takimiyla degistirilir (repo deseni).
vi.mock("react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react")>();
  return {
    ...actual,
    useState: (initial: unknown | (() => unknown)) => {
      const index = harness.stateCursor++;
      if (!(index in harness.stateValues)) {
        harness.stateValues[index] = typeof initial === "function" ? (initial as () => unknown)() : initial;
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
vi.mock("@/app/router", () => ({
  useHashRoute: () => ({ path: "/finance", params: new URLSearchParams(harness.routeParams) }),
  navigate: harness.navigate,
}));
vi.mock("@/core/api", () => ({
  api: { del: harness.apiDel, get: harness.apiGet, patch: harness.apiPatch, post: harness.apiPost },
  qs: (params: Record<string, string | number | boolean | undefined | null>) => {
    const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
    return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
  },
}));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
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

const overview = {
  year: 2026,
  month: 8,
  currencies: [
    {
      currency: "TRY",
      income: "45000.00",
      expense: "28430.00",
      net: "16570.00",
      recurring_monthly: "1240.00",
      expense_by_category: [
        { category: "rent", amount: "18000.00" },
        { category: "food", amount: "10430.00" },
      ],
      income_by_category: [{ category: "salary", amount: "45000.00" }],
    },
  ],
};
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
const incomes = [
  {
    id: "i1",
    title: "Ağustos maaşı",
    amount: "45000",
    currency: "TRY",
    category: "salary",
    received_on: "2026-08-01",
    note: null,
  },
];
const recurring = [
  {
    id: "r1",
    title: "Netflix",
    amount: "99.9",
    currency: "TRY",
    category: "subscriptions",
    billing_day: 15,
    frequency: "monthly",
    next_due_at: "2026-09-15",
    active: true,
    note: null,
    sub: "netflix",
  },
];

/**
 * Verilen sekme/ay ile sayfayi ciz; form state'i sirayla verilir.
 *
 * useState sirasi render agaciyla belirlenir: sayfa ustundeki hizli gider
 * formu (amount, category, note = 0..2) diger formlardan ONCE gelir. Bu
 * yuzden flow/subs/donut state dizileri ilk 3 yuvayi bos gecerek baslar.
 */
function render(params: string, state: unknown[] = []) {
  harness.routeParams = params;
  harness.stateCursor = 0;
  harness.stateValues = state;
  return renderToStaticMarkup(<FinancePage />);
}

/** Belirtilen uca POST/DELETE atan mutation'i bulur.

 * Ayni uca birden fazla mutation abone olabilir (sayfa ustundeki hizli
 * gider formu da /expenses'e yazar). Kacinci mutation oldugu degil,
 * gecerli goruntude hangisinin o cagriyi yaptigi onemli -- en son eslesen
 * donulur ve yalnizca onun cagrilari spy'da birakilir.
 */
function findMutation(spy: ReturnType<typeof vi.fn>, url: string, arg?: unknown) {
  let found: MutationOptions | undefined;
  let calls: unknown[][] = [];
  for (const mutation of harness.mutations) {
    spy.mockClear();
    try {
      mutation.mutationFn?.(arg);
    } catch {
      continue;
    }
    if (spy.mock.calls.some(([called]) => called === url)) {
      found = mutation;
      calls = spy.mock.calls.slice();
    }
  }
  spy.mockClear();
  for (const call of calls) spy.mock.calls.push(call);
  return found;
}

describe("finans sayfası", () => {
  beforeEach(() => {
    for (const spy of [
      harness.apiDel,
      harness.apiGet,
      harness.apiPatch,
      harness.apiPost,
      harness.invalidate,
      harness.navigate,
    ]) {
      spy.mockReset();
    }
    harness.mutations.length = 0;
    harness.queries.length = 0;
    harness.queryData = { expenses, incomes, recurring, "finance-overview": overview };
    harness.routeParams = "";
  });

  it("seçili ayın özetini tek çağrıyla çeker ve gelir/gider/net gösterir", async () => {
    const markup = render("tab=summary&month=2026-08");

    expect(markup).toContain("Ağustos 2026");
    expect(markup).toContain("Gelir");
    expect(markup).toContain("Net");
    expect(markup).toContain("Bu ay artıda");

    const byKey = (key: string) => harness.queries.find((query) => query.queryKey[0] === key);
    await byKey("finance-overview")?.queryFn();
    await byKey("expenses")?.queryFn();
    await byKey("incomes")?.queryFn();
    await byKey("recurring")?.queryFn();
    expect(harness.apiGet).toHaveBeenCalledWith("/finance/overview?year=2026&month=8");
    expect(harness.apiGet).toHaveBeenCalledWith("/expenses");
    expect(harness.apiGet).toHaveBeenCalledWith("/incomes");
    expect(harness.apiGet).toHaveBeenCalledWith("/recurring-payments");
  });

  it("donut merkezi boştayken ayın özetini, dilim üzerindeyken o kategoriyi yazar", () => {
    // SpendDonut'un tek useState'i (active dilim) 3. indekstedir -- ilk 3
    // yuva hizli gider formunun (amount, category, note) yeridir.
    const idle = render("tab=summary&month=2026-08", []);
    expect(idle).toContain("Gider");
    expect(idle).toContain("Gelir ₺45.000");
    expect(idle).toContain("Abonelik ₺1.240/ay");
    // Legend her iki kategoriyi de tasir.
    expect(idle).toContain("Kira");
    expect(idle).toContain("Market");

    // active = 1 -> ikinci dilim (Market, 10.430 / 28.430 = %36,7)
    const hovered = render("tab=summary&month=2026-08", ["", "", "", 1]);
    expect(hovered).toContain("Market");
    expect(hovered).toContain("%36,7");
    // Gobek artik ayin ozetini degil dilimi gosteriyor.
    expect(hovered).not.toContain("Abonelik ₺1.240/ay");
  });

  it("hareketler sekmesinde seçili ayın gelir ve giderlerini birlikte listeler", () => {
    // FlowTab state sirasi: kind, title, amount, category, day, filter.
    const markup = render("tab=flow&month=2026-08", ["", "", "", "expense", "", "", "food", "2026-08-26", "all"]);
    expect(markup).toContain("Market");
    expect(markup).toContain("Ağustos maaşı");
    expect(markup).toContain("Maaş");
    expect(markup).toContain("26 Ağustos");

    // Baska ay: o ayin kaydi yok. ("Market" kategori etiketi olarak acilir
    // listede zaten geciyor -- satirin varligi kayit basligiyla olculur.)
    const july = render("tab=flow&month=2026-07", ["", "", "", "expense", "", "", "food", "2026-07-01", "all"]);
    expect(july).not.toContain("Ağustos maaşı");
    expect(july).toContain("0 kayıt");
    expect(july).toContain("Kayıt yok");
  });

  it("gideri /expenses'e spent_on ile, geliri /incomes'a received_on ile yazar", () => {
    render("tab=flow", ["", "", "", "expense", "Market", "150.5", "food", "2026-08-26", "all"]);
    expect(findMutation(harness.apiPost, "/expenses")).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/expenses", {
      title: "Market",
      amount: "150.5",
      category: "food",
      spent_on: "2026-08-26",
    });

    harness.mutations.length = 0;
    render("tab=flow", ["", "", "", "income", "Ağustos maaşı", "45000", "salary", "2026-08-01", "all"]);
    expect(findMutation(harness.apiPost, "/incomes")).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/incomes", {
      title: "Ağustos maaşı",
      amount: "45000",
      category: "salary",
      received_on: "2026-08-01",
    });
  });

  it("aboneliği sıklık, ödeme günü ve addan türetilen marka ile ekler", () => {
    // SubsTab state sirasi: title, amount, frequency, billingDay
    const markup = render("tab=subs", ["", "", "", "Netflix", "99.9", "monthly", 15]);
    expect(markup).toContain("Netflix");
    expect(markup).toContain("her ayın 15");
    expect(markup).toContain("Ödendi olarak işaretle");

    expect(findMutation(harness.apiPost, "/recurring-payments")).toBeDefined();
    const [, body] = harness.apiPost.mock.calls.find(([url]) => url === "/recurring-payments")!;
    expect(body).toMatchObject({
      title: "Netflix",
      amount: "99.9",
      category: "subscriptions",
      frequency: "monthly",
      billing_day: 15,
      sub: "netflix",
    });
    expect(String((body as { next_due_at: string }).next_due_at)).toMatch(/^\d{4}-\d{2}-15$/);
  });

  it("satır içi düzeltmeyi kaydın türüne göre doğru PATCH ucuna yazar", () => {
    // FlowTab state sirasi: kind, title, amount, category, day, filter,
    // editingId, editTitle, editAmount
    const editing = ["", "", "", "expense", "", "", "food", "2026-08-26", "all", "e1", "Market (düzeltildi)", "200"];
    const markup = render("tab=flow&month=2026-08", editing);
    expect(markup).toContain("Kaydet");
    expect(markup).toContain("Vazgeç");

    expect(findMutation(harness.apiPatch, "/expenses/e1", { id: "e1", kind: "expenses" })).toBeDefined();
    expect(harness.apiPatch).toHaveBeenCalledWith("/expenses/e1", {
      title: "Market (düzeltildi)",
      amount: "200",
    });

    harness.mutations.length = 0;
    render("tab=flow&month=2026-08", [...editing.slice(0, 9), "i1", "Ağustos maaşı", "46000"]);
    expect(findMutation(harness.apiPatch, "/incomes/i1", { id: "i1", kind: "incomes" })).toBeDefined();
    expect(harness.apiPatch).toHaveBeenCalledWith("/incomes/i1", {
      title: "Ağustos maaşı",
      amount: "46000",
    });
  });

  it("ödeme ve silme işlemlerini doğru uçlara gönderip finance.write ile tazeler", () => {
    render("tab=subs", ["", "", "", "", "", "monthly", 1]);

    const pay = findMutation(harness.apiPost, "/recurring-payments/r1/pay", "r1");
    expect(pay).toBeDefined();
    pay?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("finance.write");

    harness.invalidate.mockReset();
    const remove = findMutation(harness.apiDel, "/incomes/i1", { id: "i1", kind: "incomes" });
    expect(remove).toBeDefined();
    remove?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("finance.write");
  });

  it("aylık akış çubuk grafiğini /finance/summary verisiyle çizer", async () => {
    harness.queryData["finance-summary"] = [
      { month: "2026-03", income: 40000, expense: 25000 },
      { month: "2026-04", income: 41000, expense: 26000 },
      { month: "2026-05", income: 42000, expense: 24000 },
      { month: "2026-06", income: 43000, expense: 27000 },
      { month: "2026-07", income: 44000, expense: 28000 },
      { month: "2026-08", income: 45000, expense: 28430 },
    ];
    const markup = render("tab=summary&month=2026-08");

    expect(markup).toContain("Aylık akış");
    expect(markup).toContain("Son 6 ay · gelir / gider");
    // Eksen etiketleri kisa ay adlariyla; grafik bos veri uyarisi gostermiyor.
    for (const short of ["Mar", "Nis", "May", "Haz", "Tem", "Ağu"]) {
      expect(markup).toContain(short);
    }
    expect(markup).not.toContain("Grafik için veri yok.");
    // Cubuklar tema tokenlariyla (sabit hex yok) ve erisilebilir adla.
    expect(markup).toContain('fill="var(--success)"');
    expect(markup).toContain('fill="var(--danger)"');
    expect(markup).toContain('aria-label="Son 6 ayın gelir ve gider çubuk grafiği"');

    const byKey = (key: string) => harness.queries.find((query) => query.queryKey[0] === key);
    await byKey("finance-summary")?.queryFn();
    expect(harness.apiGet).toHaveBeenCalledWith("/finance/summary?months=6");
  });

  it("son 30 gün giderlerini en büyük 5 + Diğer olarak dağıtır", () => {
    const day = (daysAgo: number) => {
      const key = todayKey();
      const d = new Date(key + "T00:00:00Z");
      d.setUTCDate(d.getUTCDate() - daysAgo);
      return d.toISOString().slice(0, 10);
    };
    harness.queryData.expenses = [
      { id: "e1", title: "Market", amount: "150.5", currency: "TRY", category: "food", spent_on: day(1), note: null, sub: null },
      { id: "e2", title: "Kira", amount: "18000", currency: "TRY", category: "rent", spent_on: day(2), note: null, sub: null },
      { id: "e3", title: "Ulaşım", amount: "300", currency: "TRY", category: "transport", spent_on: day(3), note: null, sub: null },
      { id: "e4", title: "Fatura", amount: "400", currency: "TRY", category: "bills", spent_on: day(4), note: null, sub: null },
      { id: "e5", title: "Sağlık", amount: "500", currency: "TRY", category: "health", spent_on: day(5), note: null, sub: null },
      { id: "e6", title: "Eğlence", amount: "600", currency: "TRY", category: "entertainment", spent_on: day(6), note: null, sub: null },
      // Pencerenin disinda (40 gun once): barlara girmemeli.
      { id: "e7", title: "Eski borç", amount: "999", currency: "TRY", category: "shopping", spent_on: day(40), note: null, sub: null },
    ];
    const markup = render("tab=summary&month=2026-08");

    expect(markup).toContain("Son 30 gün · kategori dağılımı");
    // En buyuk 5: Kira, Eğlence, Sağlık, Fatura, Ulaşım -- geri kalan "Diğer".
    expect(markup).toContain("Kira");
    expect(markup).toContain("Eğlence");
    expect(markup).toContain("Diğer");
    // Pencere disindaki "Eski borç" bar uretmez.
    expect(markup).not.toContain("Eski borç");
  });

  it("hızlı gider formu tutar+kategori+not ile /expenses'e yazar", () => {
    // QuickAdd state sirasi: amount, category, note (sayfa ustunde, once).
    const markup = render("tab=summary&month=2026-08", ["55.5", "food", "Market alışverişi"]);
    expect(markup).toContain("Hızlı gider ekle");

    const quickAdd = findMutation(harness.apiPost, "/expenses");
    expect(quickAdd).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/expenses", {
      title: "Market alışverişi",
      amount: "55.5",
      category: "food",
      note: "Market alışverişi",
      spent_on: todayKey(),
    });
  });

  it("hızlı giderde not boşsa başlığı kategori adından türer", () => {
    render("tab=summary", ["20", "transport", ""]);
    expect(findMutation(harness.apiPost, "/expenses")).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith(
      "/expenses",
      expect.objectContaining({ title: "Ulaşım", amount: "20", category: "transport", note: null }),
    );
  });

  it("özet kartlarında bu ay vs geçen ay trendini gösterir", () => {
    harness.queryData["finance-summary"] = [
      { month: "2026-03", income: 40000, expense: 25000 },
      { month: "2026-04", income: 41000, expense: 26000 },
      { month: "2026-05", income: 42000, expense: 24000 },
      { month: "2026-06", income: 43000, expense: 27000 },
      { month: "2026-07", income: 40000, expense: 25000 },
      { month: "2026-08", income: 45000, expense: 20000 },
    ];
    const markup = render("tab=summary&month=2026-08");

    // Gelir %12,5 artti (40.000 -> 45.000); gider %20 dustu (25.000 -> 20.000).
    expect(markup).toContain("▲ %13 vs geçen ay");
    expect(markup).toContain("▼ %20 vs geçen ay");
  });
});
