import { describe, expect, it, vi } from "vitest";
import { parseTaskText } from "./taskParser";
import { todayKey, tomorrowKey } from "./date";

// Istanbul sinir testleri icin sabit an: 2026-08-29T21:30:00Z = Istanbul 30.08 00:30.
const ISTANBUL_NIGHT = new Date("2026-08-29T21:30:00Z");

describe("Turkce gorev ayristirici (Faz 23)", () => {
  it("'bugun' plan_day uretir, due_at uretmez", () => {
    const result = parseTaskText("bugün öğrenme planını tamamla");
    expect(result.plan_day).toBe(todayKey());
    expect(result.due_at).toBeUndefined();
    expect(result.title).toBe("öğrenme planını tamamla");
    expect(result.consumed).toContain("bugün");
  });

  it("'bugun teslim' / 'son tarih bugun' due_at uretir, plan_day YOK", () => {
    const a = parseTaskText("bugün teslim rapor");
    expect(a.due_at).toBeDefined();
    expect(a.plan_day).toBeUndefined();
    const b = parseTaskText("son tarih bugün rapor");
    expect(b.due_at).toBeDefined();
    expect(b.plan_day).toBeUndefined();
    expect(b.title).toBe("rapor");
  });

  it("'yarin 14:00' plan + saat onerir, baslik temizlenir", () => {
    const result = parseTaskText("yarın 14:00 dişçiyi ara");
    expect(result.plan_day).toBe(tomorrowKey());
    expect(result.time).toBe("14:00");
    expect(result.title).toBe("dişçiyi ara");
  });

  it("'cuma projeyi gonder' bir sonraki cuma gunune planlar", () => {
    // 2026-08-29 Cumartesi (Istanbul) -> sonraki cuma 2026-09-04.
    const result = parseTaskText("cuma projeyi gönder", new Date("2026-08-29T10:00:00Z"));
    expect(result.plan_day).toBe("2026-09-04");
    expect(result.title).toBe("projeyi gönder");
  });

  it("Pazar gecisi: pazar gecesi 'yarin' pazartesiye gider", () => {
    // Istanbul 30.08 00:30 (Pazar gecesi) -> yarin Pazartesi 31.08.
    const result = parseTaskText("yarın toplantı", ISTANBUL_NIGHT);
    expect(result.plan_day).toBe("2026-08-31");
  });

  it("Türkçe karakterli gun adlari ve etiketler", () => {
    const result = parseTaskText("pazartesi #iş başvuruları kontrol et");
    expect(result.plan_day).toBe("2026-08-31");
    expect(result.tags).toEqual(["iş"]);
    expect(result.title).toBe("başvuruları kontrol et");
  });

  it("'yuksek oncelik' ve 'acil' oncelik onerir", () => {
    expect(parseTaskText("yüksek öncelik cuma CV gönder").priority).toBe(3);
    expect(parseTaskText("acil destek çağrısı").priority).toBe(3);
    expect(parseTaskText("düşük öncelik temizlik").priority).toBe(1);
  });

  it("'ayin 1'inde' ayin gunune planlar", () => {
    const result = parseTaskText("ayın 1'inde faturaları kontrol et", new Date("2026-08-29T10:00:00Z"));
    expect(result.plan_day).toBe("2026-09-01");
  });

  it("'gelecek hafta' onumuzdeki pazartesiye planlar ve uyarir", () => {
    // 2026-08-29 Cumartesi: bu hafta 24-30, gelecek hafta 31-08'de baslar.
    const result = parseTaskText("gelecek hafta raporu bitir", new Date("2026-08-29T10:00:00Z"));
    expect(result.plan_day).toBe("2026-08-31");
    expect(result.warnings.length).toBeGreaterThan(0);
  });

  it("ayristirilamayan metin oldugu gibi kalir", () => {
    const result = parseTaskText("alışveriş listesi yaz");
    expect(result.title).toBe("alışveriş listesi yaz");
    expect(result.plan_day).toBeUndefined();
    expect(result.consumed).toEqual([]);
    expect(result.warnings).toEqual([]);
  });

  it("deadline + saat: due_at Istanbul saatine gore UTC'ye cevrilir", () => {
    const result = parseTaskText("yarın 14:00 teslim rapor", new Date("2026-08-29T10:00:00Z"));
    expect(result.due_at).toBeDefined();
    // Istanbul 14:00 = UTC 11:00; o gunun ISO'su.
    const due = new Date(result.due_at!);
    expect(due.toISOString()).toBe("2026-08-30T11:00:00.000Z");
  });

  it("network cagrisi yok: parser saf bir fonksiyondur", () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    parseTaskText("yarın koşu");
    expect(fetchSpy).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
