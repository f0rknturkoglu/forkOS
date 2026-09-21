/**
 * Fiil sozlugu: olay -> insan dili ve aile ikonu.
 *
 * Uyari (alerts) kurali burada DEGIL: sunucu `is_alert` bayragini doner
 * (bkz. backend tests/test_activity_filters.py), istemci liste tutmaz.
 */

import { describe as describeEvent, verbIcon } from "./verbs";
import { describe, expect, it } from "vitest";

describe("describe", () => {
  it("etiketi payload ayrıntısıyla tek cümleye çevirir", () => {
    expect(describeEvent("todo.completed", { title: "Raporu bitir" })).toBe("Görev tamamlandı — Raporu bitir");
    expect(describeEvent("rss.items_added", { count: 12 })).toBe("Yeni RSS yazıları (12)");
  });

  it("ayrıntı sırası: mesaj > taşıma > başlık > adres", () => {
    expect(describeEvent("bookmark.moved", { from: "inbox", to: "learning" })).toBe(
      "Yer imi taşındı — inbox → learning",
    );
    expect(describeEvent("rss.feed_failed", { message: "zaman aşımı", title: "Besleme", url: "https://x" })).toBe(
      "Besleme hata verdi — zaman aşımı",
    );
    expect(describeEvent("bookmark.saved", { url: "https://x" })).toBe("Yer imi kaydedildi — https://x");
  });

  it("tanımadığı fiili okunur yedeğe çevirir (ham anahtar göstermez)", () => {
    expect(describeEvent("bilinmeyen.fiil", {})).toBe("Fiil");
    expect(describeEvent("yeni_modul.some_new_verb", {})).not.toContain("yeni_modul");
  });
});

describe("verbIcon", () => {
  it("aynı ailenin fiillerine aynı ikonu verir", () => {
    expect(verbIcon("todo.completed")).toBe(verbIcon("todo.created"));
    expect(verbIcon("recurring.paid")).toBe(verbIcon("recurring_payment.created"));
    expect(verbIcon("todo.completed")).not.toBe(verbIcon("pomodoro.completed"));
  });

  it("tanımadığı fiilde nötr ikona düşer", () => {
    expect(verbIcon("bilinmeyen.fiil")).toBe(verbIcon(""));
  });
});
