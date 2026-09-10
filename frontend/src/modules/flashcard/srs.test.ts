// @vitest-environment node

/**
 * SM-2 tahmini backend ile ayni sabitleri kullanmali: arayuzde "3 gün" yazan
 * bir derece, sunucuda baska bir aralik uretirse kullaniciya yalan soylenmis
 * olur. Bu test iki tarafin kurallarini birlikte dogrular.
 */

import { describe, expect, it } from "vitest";
import { formatInterval, predictInterval, predictNextIntervals } from "./srs";

describe("SRS aralık tahmini", () => {
  it("yeni kartta dereceye göre ilk aralığı verir", () => {
    const fresh = { interval_days: 0, ease: 2.5, isNew: true };

    expect(predictInterval(fresh, 0)).toEqual({ days: 0, minutes: 10 });
    expect(predictInterval(fresh, 1)).toEqual({ days: 1, minutes: null });
    expect(predictInterval(fresh, 2)).toEqual({ days: 1, minutes: null });
    expect(predictInterval(fresh, 3)).toEqual({ days: 4, minutes: null });
  });

  it("görülmüş kartta aralığı ease ile büyütür", () => {
    const card = { interval_days: 10, ease: 2.5, isNew: false };

    // 0: yariya duser, 1: %20 artar, 2: ease kadar, 3: ease x 1.3
    expect(predictInterval(card, 0).days).toBe(5);
    expect(predictInterval(card, 1).days).toBe(12);
    expect(predictInterval(card, 2).days).toBe(25);
    // 3: ease 2.5 -> 2.65, sonra x1.3: 10 * 2.65 * 1.3 = 34.45 -> 34
    expect(predictInterval(card, 3).days).toBe(34);
  });

  it("ease tabana iner, sıfırın altına düşmez", () => {
    const low = { interval_days: 4, ease: 1.3, isNew: false };
    // Ust uste "Yine" ease'i 1.3'un altina indirmemeli: 4 * max(1.3, 1.1) = 5.
    expect(predictInterval(low, 0).days).toBe(2);
    expect(predictInterval({ ...low, interval_days: 30 }, 0).days).toBe(15);
  });

  it("süreyi insan diline çevirir", () => {
    expect(formatInterval(0, 10)).toBe("10 dk");
    expect(formatInterval(1, null)).toBe("1 gün");
    expect(formatInterval(45, null)).toBe("2 ay");
    expect(formatInterval(400, null)).toBe("1.1 yıl");
  });

  it("dört dereceyi tonlarıyla birlikte döner", () => {
    const rows = predictNextIntervals({ interval_days: 9, ease: 2.5, isNew: false });

    expect(rows.map((row) => row.label)).toEqual(["Yine", "Zor", "İyi", "Kolay"]);
    expect(rows.map((row) => row.tone)).toEqual(["danger", "warn", "primary", "ok"]);
    // 9 gunluk kart: 0 -> 5 gun, 1 -> 11 gun, 2 -> 23 gun, 3 -> 31 gun ("1 ay").
    expect(rows.map((row) => row.hint)).toEqual(["5 gün", "11 gün", "23 gün", "1 ay"]);
  });
});
