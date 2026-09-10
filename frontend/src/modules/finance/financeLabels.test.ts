import { describe, expect, it } from "vitest";
import {
  billingLabel,
  categoryIcon,
  categoryLabel,
  dayOrdinal,
  dueLabel,
  frequencyLabel,
  money,
  monthKeyOf,
  monthlyShare,
  monthLabel,
  monthShort,
  parseMonth,
  percent,
  shiftMonth,
  signedMoney,
  subColor,
  subSlug,
} from "./financeLabels";
import { EXPENSE_CATEGORIES, INCOME_CATEGORIES } from "./financeLabels";

describe("finans etiketleri", () => {
  it("kategori ve sıklığı Türkçeleştirir, bilinmeyeni ham bırakır", () => {
    expect(categoryLabel("food")).toBe("Market");
    expect(categoryLabel("salary")).toBe("Maaş");
    expect(frequencyLabel("quarterly")).toBe("3 aylık");
    expect(categoryLabel("kripto")).toBe("kripto");
  });

  it("tutarı tr-TR biçiminde yazar, geçersiz kurda çökmez", () => {
    expect(money("150.5", "TRY")).toContain("150,50");
    expect(money(1200, "TRY", 0)).not.toContain(",");
    // Gecersiz kur kodu Intl'i patlatir; sayi + kod'a dusmeli.
    expect(money(10, "XX")).toContain("10");
  });

  it("dilim payını yüzdeye çevirir", () => {
    expect(percent(0.3668)).toBe("%36,7");
    expect(percent(1)).toBe("%100");
    expect(percent(Number.NaN)).toBe("—");
  });

  it("net tutarı işaretli gösterir", () => {
    expect(signedMoney(500, "TRY")).toMatch(/^\+/);
    expect(signedMoney(-500, "TRY")).toMatch(/^−/);
    expect(signedMoney(0, "TRY")).not.toMatch(/^[+−]/);
  });
});

describe("ödeme ritmi", () => {
  it("Türkçe sıra ekini son rakama göre verir", () => {
    expect(dayOrdinal(1)).toBe("1’i");
    expect(dayOrdinal(3)).toBe("3’ü");
    expect(dayOrdinal(6)).toBe("6’sı");
    expect(dayOrdinal(15)).toBe("15’i");
    // Onluklar kendi okunusuyla ayrisir: 10'u, 20'si, 30'u.
    expect(dayOrdinal(10)).toBe("10’u");
    expect(dayOrdinal(20)).toBe("20’si");
    expect(dayOrdinal(30)).toBe("30’u");
  });

  it("sıklığı ve ödeme gününü tek cümlede birleştirir", () => {
    expect(billingLabel("monthly", 15)).toBe("her ayın 15’i");
    expect(billingLabel("yearly", 20)).toBe("yılda bir, ayın 20’si");
    expect(billingLabel("quarterly", 3)).toBe("3 ayda bir, ayın 3’ü");
    // Odeme gunu yoksa yalin siklik etiketi.
    expect(billingLabel("monthly", null)).toBe("Aylık");
  });
});

describe("ay gezinme", () => {
  it("ay anahtarını kaydırır ve yıl sınırını aşar", () => {
    expect(shiftMonth("2026-08", 1)).toBe("2026-09");
    expect(shiftMonth("2026-12", 1)).toBe("2027-01");
    expect(shiftMonth("2026-01", -1)).toBe("2025-12");
  });

  it("gün anahtarından ay anahtarı çıkarır ve okunur etiket verir", () => {
    expect(monthKeyOf("2026-08-26")).toBe("2026-08");
    expect(parseMonth("2026-08")).toEqual({ year: 2026, month: 8 });
    expect(monthLabel("2026-08")).toBe("Ağustos 2026");
  });

  it("grafik ekseni icin kisa ay adi verir", () => {
    expect(monthShort("2026-08")).toBe("Ağu");
    expect(monthShort("2026-03")).toBe("Mar");
  });

  it("vade uzaklığını insan diliyle söyler", () => {
    expect(dueLabel(0)).toBe("bugün");
    expect(dueLabel(1)).toBe("yarın");
    expect(dueLabel(3)).toBe("3 gün sonra");
    expect(dueLabel(-2)).toBe("2 gün gecikti");
  });
});

describe("abonelik markası", () => {
  it("baslıktan backend'in kabul ettiği slug üretir", () => {
    expect(subSlug("Netflix")).toBe("netflix");
    expect(subSlug("Amazon Prime")).toBe("amazon_prime");
    // Turkce karakterler ASCII'ye duser; slug [a-z0-9_] kalir.
    expect(subSlug("Şirket Üyeliği")).toBe("sirket_uyeligi");
    expect(subSlug("!!!")).toBeNull();
  });

  it("aynı markaya her zaman aynı rengi verir", () => {
    expect(subColor("netflix")).toBe(subColor("netflix"));
    expect(subColor("bilinmeyen_marka")).toBe(subColor("bilinmeyen_marka"));
    expect(subColor("netflix")).toMatch(/^var\(--chart-\d\)$/);
    expect(subColor("bilinmeyen_marka")).toMatch(/^var\(--chart-\d\)$/);
  });
});

describe("kategori ikonları", () => {
  it("her kategori için ikon ve etiket tanımlı", () => {
    for (const category of [...EXPENSE_CATEGORIES, ...INCOME_CATEGORIES]) {
      expect(categoryLabel(category), category).not.toBe(category);
      expect(categoryIcon(category), category).toBeTypeOf("object");
    }
  });

  it("bilinmeyen kategori ikon isterken çökmez", () => {
    expect(categoryIcon("kripto")).toBeTypeOf("object");
  });
});

describe("aylık yük payı", () => {
  it("sıklığa göre bir aya düşen tutarı verir", () => {
    expect(monthlyShare("1200", "yearly")).toBe(100);
    expect(monthlyShare(300, "quarterly")).toBe(100);
    expect(monthlyShare("99.9", "monthly")).toBeCloseTo(99.9);
    // Bilinmeyen siklik aylik sayilir (backend ile ayni sozlesme).
    expect(monthlyShare(50, "weekly")).toBe(50);
  });
});
