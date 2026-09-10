// @vitest-environment jsdom

/**
 * Finans sayfasi: ozet, hareketler ve abonelikler.
 *
 * Eski test SSR + useState-cursor takimiydi; sayfa bilesenlere bolunup
 * modallara gecince state sirasi degisti. Bu dosya artik gercek etkilesimi
 * olcer: tikla, yaz, kaydet -- ve gonderilen istekleri dogrular.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { todayKey } from "@/lib/date";
import { FinancePage } from "./FinancePage";

const confirmDialog = vi.fn(async () => true);
vi.mock("@/core/dialog", () => ({ confirmDialog: vi.fn(async () => true), DialogHost: () => null }));
vi.mock("@/core/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), put: vi.fn() },
  qs: (params: Record<string, string | number | boolean | undefined | null>) => {
    const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
    return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
  },
}));
// Gercek hash router gibi davranir: navigate hash'i yazar, hook hashchange'i dinler.
vi.mock("@/app/router", async () => {
  const { useEffect, useState } = await import("react");
  return {
    useHashRoute: () => {
      const [hash, setHash] = useState(() => location.hash);
      useEffect(() => {
        const onChange = () => setHash(location.hash);
        window.addEventListener("hashchange", onChange);
        return () => window.removeEventListener("hashchange", onChange);
      }, []);
      return { path: "/finance", params: new URLSearchParams(hash.split("?")[1] ?? "") };
    },
    navigate: (path: string) => {
      location.hash = `#${path}`;
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    },
  };
});

import { confirmDialog as confirmMock } from "@/core/dialog";
import { api } from "@/core/api";

const apiGet = vi.mocked(api.get);
const apiPost = vi.mocked(api.post);
const apiPatch = vi.mocked(api.patch);
const apiDel = vi.mocked(api.del);
const apiPut = vi.mocked(api.put);
const dialogSpy = vi.mocked(confirmMock);

const TODAY = todayKey();
const YESTERDAY = (() => {
  const d = new Date(`${TODAY}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
})();
const MONTH = TODAY.slice(0, 7);

const overview = {
  year: Number(MONTH.slice(0, 4)),
  month: Number(MONTH.slice(5, 7)),
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
    {
      currency: "USD",
      income: "1000.00",
      expense: "200.00",
      net: "800.00",
      recurring_monthly: "10.00",
      expense_by_category: [{ category: "shopping", amount: "200.00" }],
      income_by_category: [],
    },
  ],
};

const expenses = [
  {
    id: "e1",
    title: "Migros",
    amount: "150.5",
    currency: "TRY",
    category: "food",
    spent_on: TODAY,
    note: null,
    sub: null,
  },
  {
    id: "e2",
    title: "Kira",
    amount: "18000",
    currency: "TRY",
    category: "rent",
    spent_on: YESTERDAY,
    note: null,
    sub: null,
  },
  {
    id: "e3",
    title: "Amazon",
    amount: "30",
    currency: "USD",
    category: "shopping",
    spent_on: TODAY,
    note: null,
    sub: null,
  },
];

const incomes = [
  {
    id: "i1",
    title: "Maaş",
    amount: "45000",
    currency: "TRY",
    category: "salary",
    received_on: TODAY,
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
    next_due_at: TODAY,
    active: true,
    note: null,
    sub: "netflix",
  },
  {
    id: "r2",
    title: "iCloud",
    amount: "1200",
    currency: "TRY",
    category: "subscriptions",
    billing_day: 5,
    frequency: "yearly",
    next_due_at: TODAY,
    active: true,
    note: null,
    sub: "icloud",
  },
];

function renderPage(params = `tab=summary&month=${MONTH}`) {
  location.hash = `#/finance?${params}`;
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <FinancePage />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  for (const spy of [apiGet, apiPost, apiPatch, apiDel, apiPut]) spy.mockReset();
  dialogSpy.mockClear();
  dialogSpy.mockResolvedValue(true);
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: { getItem: () => null } });
  apiGet.mockImplementation(async (path: string) => {
    if (path.startsWith("/finance/overview")) return overview;
    if (path.startsWith("/finance/summary")) {
      return [
        { month: "2026-07", income: 40000, expense: 30000 },
        { month: MONTH, income: 45000, expense: 28430 },
      ];
    }
    if (path === "/expenses") return expenses;
    if (path === "/incomes") return incomes;
    if (path === "/recurring-payments") return recurring;
    if (path === "/settings") return { "finance.monthly_budget": {} };
    return [];
  });
  apiPost.mockResolvedValue({});
  apiPatch.mockResolvedValue({});
  apiDel.mockResolvedValue(undefined);
  apiPut.mockResolvedValue({});
});

afterEach(cleanup);

describe("özet sekmesi", () => {
  it("hero bakiyeyi, üç sütunu ve kategori dağılımını gösterir", async () => {
    renderPage();

    await screen.findByText("Net durum");
    expect(await screen.findByText("₺16.570")).toBeTruthy();
    expect(screen.getByText("Sabit faturalar")).toBeTruthy();
    expect(screen.getByText("₺1.240")).toBeTruthy();
    expect(screen.getByText("/ay")).toBeTruthy();
    // Segmentli bar: iki kategori + yüzdeleri.
    expect(screen.getByRole("img", { name: /harcama dağılımı/i })).toBeTruthy();
    // "Kira" hem bar legend'inda hem icgoru cumlesinde gecer.
    expect(screen.getAllByText("Kira").length).toBeGreaterThan(0);
    expect(screen.getByText("%63,3")).toBeTruthy();
    // Akilli icgoru: bu ayin en buyuk kalemi + gecen aya gore degisim.
    expect(screen.getByText(/en büyük harcama kalemin/)).toBeTruthy();
  });

  it("bütçe tanımlıysa kalan bütçeyi ve harcama yüzdesini gösterir, kaydeder", async () => {
    apiGet.mockImplementation(async (path: string) => {
      if (path === "/settings") return { "finance.monthly_budget": { TRY: 40000 } };
      if (path.startsWith("/finance/overview")) return overview;
      if (path === "/expenses") return expenses;
      if (path === "/incomes") return incomes;
      if (path === "/recurring-payments") return recurring;
      return [];
    });
    renderPage();

    expect(await screen.findByText("₺11.570")).toBeTruthy();
    expect(screen.getByText("Kalan bütçe")).toBeTruthy();
    expect(screen.getByText(/%71,1 harcandı/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Bütçeyi düzenle" }));
    const field = screen.getByLabelText("Aylık bütçe");
    fireEvent.change(field, { target: { value: "50000" } });
    fireEvent.click(screen.getByRole("button", { name: /Kaydet/ }));

    await waitFor(() =>
      expect(apiPut).toHaveBeenCalledWith("/settings/finance.monthly_budget", { value: { TRY: 50000 } }),
    );
  });

  it("para birimi hapı seçimi özeti ve hareketleri o birime çevirir", async () => {
    renderPage();

    await screen.findByText("₺16.570");
    fireEvent.click(screen.getAllByRole("button", { name: "USD" })[0]);

    // Ozet artik USD blogunu gosterir; TRY kalemleri gorunmez.
    expect(await screen.findByText("$800")).toBeTruthy();
    expect(screen.queryByText("₺16.570")).toBeNull();
  });
});

describe("hareketler sekmesi", () => {
  it("gün bloklarında listeler, arama ve tür filtresi uygular", async () => {
    renderPage(`tab=flow&month=${MONTH}`);

    // Gun bloklari: Bugun ve Dun baslikleri (veri gelince).
    expect(await screen.findByText("Bugün")).toBeTruthy();
    expect(screen.getByText("Dün")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Migros hareketini düzenle" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Kira hareketini düzenle" })).toBeTruthy();
    // USD hareketi TRY gorunumunde listelenmez (para birimi filtresi).
    expect(screen.queryByRole("button", { name: "Amazon hareketini düzenle" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Gelirler" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Migros hareketini düzenle" })).toBeNull());
    expect(screen.getByRole("button", { name: "Maaş hareketini düzenle" })).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Hareketlerde ara"), { target: { value: "yok-boyle" } });
    await waitFor(() => expect(screen.getByText("Kayıt yok")).toBeTruthy());

    fireEvent.click(screen.getByRole("button", { name: "Tümü" }));
    fireEvent.change(screen.getByLabelText("Hareketlerde ara"), { target: { value: "kira" } });
    await waitFor(() => expect(screen.queryByRole("button", { name: "Migros hareketini düzenle" })).toBeNull());
    expect(screen.getByRole("button", { name: "Kira hareketini düzenle" })).toBeTruthy();
  });

  it("sayı olarak gelen tutarla aramada çökmez, tutarla eşleşir (canlı hata)", async () => {
    // Backend Decimal'i JSON'da SAYI dondurur; eski kod `.includes` cagirip
    // sayfayi cokertiyordu (canli dogrulamada yakalandi).
    apiGet.mockImplementation(async (path: string) => {
      if (path.startsWith("/finance/overview")) return overview;
      if (path === "/expenses") return [{ ...expenses[0], amount: 250.0 }];
      if (path === "/incomes") return [];
      if (path === "/recurring-payments") return [];
      if (path === "/settings") return { "finance.monthly_budget": {} };
      return [];
    });
    renderPage(`tab=flow&month=${MONTH}`);

    const search = await screen.findByLabelText("Hareketlerde ara");
    fireEvent.change(search, { target: { value: "250" } });
    expect(await screen.findByRole("button", { name: "Migros hareketini düzenle" })).toBeTruthy();

    fireEvent.change(search, { target: { value: "zzz-bulunmaz" } });
    expect(await screen.findByText("Kayıt yok")).toBeTruthy();
  });

  it("satıra tıklayınca düzenleme modalı açılır ve PATCH atar", async () => {
    renderPage(`tab=flow&month=${MONTH}`);

    fireEvent.click(await screen.findByRole("button", { name: "Migros hareketini düzenle" }));
    const dialog = await screen.findByRole("dialog", { name: "Hareketi düzenle" });

    fireEvent.change(within(dialog).getByLabelText("Tutar"), { target: { value: "222" } });
    fireEvent.change(within(dialog).getByLabelText("Açıklama"), { target: { value: "Migros (düzeltildi)" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kaydet" }));

    await waitFor(() =>
      expect(apiPatch).toHaveBeenCalledWith("/expenses/e1", {
        title: "Migros (düzeltildi)",
        amount: "222",
        category: "food",
        spent_on: TODAY,
      }),
    );
  });

  it("düzenleme modalından onaylı silme DELETE atar", async () => {
    renderPage(`tab=flow&month=${MONTH}`);

    fireEvent.click(await screen.findByRole("button", { name: "Kira hareketini düzenle" }));
    const dialog = await screen.findByRole("dialog", { name: "Hareketi düzenle" });
    fireEvent.click(within(dialog).getByRole("button", { name: /Sil/ }));

    await waitFor(() => expect(dialogSpy).toHaveBeenCalled());
    await waitFor(() => expect(apiDel).toHaveBeenCalledWith("/expenses/e2"));
  });
});

describe("ekleme modalı", () => {
  it("yeni ekle düğmesiyle açılır ve gideri /expenses'e yazar", async () => {
    renderPage();
    await screen.findByText("Net durum");

    fireEvent.click(screen.getByRole("button", { name: /Yeni ekle/ }));
    const dialog = await screen.findByRole("dialog", { name: "Yeni ekle" });

    fireEvent.change(within(dialog).getByLabelText("Tutar"), { target: { value: "55.5" } });
    fireEvent.change(within(dialog).getByLabelText("Açıklama"), { target: { value: "Market alışverişi" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kaydet" }));

    await waitFor(() =>
      expect(apiPost).toHaveBeenCalledWith("/expenses", {
        title: "Market alışverişi",
        amount: "55.5",
        currency: "TRY",
        category: "food",
        note: null,
        spent_on: TODAY,
      }),
    );
  });

  it("abonelik türünde sıklık ve ödeme günüyle /recurring-payments'e yazar", async () => {
    renderPage(`tab=subs&month=${MONTH}`);
    await screen.findByText("₺200");

    fireEvent.click(screen.getByRole("button", { name: /Yeni ekle/ }));
    const dialog = await screen.findByRole("dialog", { name: "Yeni ekle" });

    fireEvent.click(
      within(within(dialog).getByRole("tablist", { name: "Kayıt türü" })).getByRole("button", { name: "Abonelik" }),
    );
    fireEvent.change(within(dialog).getByLabelText("Tutar"), { target: { value: "149.99" } });
    fireEvent.change(within(dialog).getByLabelText("Abonelik adı"), { target: { value: "Spotify" } });
    fireEvent.change(within(dialog).getByLabelText("Ödeme günü"), { target: { value: "20" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kaydet" }));

    await waitFor(() => {
      const call = apiPost.mock.calls.find(([path]) => path === "/recurring-payments");
      expect(call).toBeTruthy();
      expect(call?.[1]).toMatchObject({
        title: "Spotify",
        amount: "149.99",
        currency: "TRY",
        category: "subscriptions",
        frequency: "monthly",
        billing_day: 20,
        sub: "spotify",
      });
      expect(String((call?.[1] as { next_due_at: string }).next_due_at)).toMatch(/^\d{4}-\d{2}-20$/);
    });
  });

  it("n kısayolu modalı açar, metin alanındayken açmaz", async () => {
    renderPage();
    await screen.findByText("Net durum");

    fireEvent.keyDown(window, { key: "n" });
    expect(await screen.findByRole("dialog", { name: "Yeni ekle" })).toBeTruthy();
    fireEvent.keyDown(document.body, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Yeni ekle" })).toBeNull());

    // Metin alanindayken kisayol harf yutmaz.
    fireEvent.click(screen.getByRole("button", { name: "Hareketler" }));
    const search = await screen.findByLabelText("Hareketlerde ara");
    fireEvent.change(search, { target: { value: "" } });
    fireEvent.keyDown(search, { key: "n" });
    expect(screen.queryByRole("dialog", { name: "Yeni ekle" })).toBeNull();
  });
});

describe("abonelikler sekmesi", () => {
  it("aylık yükü ve yıllık izdüşümü gösterir, ödemeyi işler", async () => {
    renderPage(`tab=subs&month=${MONTH}`);

    // Netflix 99,9/ay + iCloud 1200/yil (=100/ay) -> 199,9/ay; yillik 2.399
    expect(await screen.findByText("₺200")).toBeTruthy();
    expect(screen.getByText("Aylık sabit yük")).toBeTruthy();
    expect(screen.getByText("₺2.399")).toBeTruthy();
    expect(screen.getByText("2 aktif abonelik")).toBeTruthy();

    fireEvent.click(screen.getAllByRole("button", { name: /Ödendi/ })[0]);
    await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/recurring-payments/r1/pay"));
    await waitFor(() =>
      expect(screen.getByText(/Netflix ödemesi yapıldı ve bu ayın harcamalarına eklendi\./)).toBeTruthy(),
    );
  });
});
