import { describe, expect, it } from "vitest";
import {
  addAppDays,
  appDateTimeInputToUtc,
  appDateTimeInputValue,
  appLocalToUtc,
  appDayUtc,
  appTimeParts,
  appWeekKeys,
  appWeekStartKey,
  daysBetween,
  isSameAppDay,
  keyToUtc,
  localDateKey,
  todayKey,
  tomorrowKey,
} from "./date";

describe("ortak tarih/saat sozlesmesi (Faz 14)", () => {
  it("2026-01-14T21:30:00Z Istanbul'da ertesi gundur", () => {
    expect(localDateKey(new Date("2026-01-14T21:30:00Z"))).toBe("2026-01-15");
  });

  it("Istanbul sabahina denk gelen UTC ani ayni gundur", () => {
    expect(localDateKey(new Date("2026-01-14T06:00:00Z"))).toBe("2026-01-14");
  });

  it("isSameAppDay sinirda ayni gunu tanir", () => {
    expect(isSameAppDay(new Date("2026-01-14T21:30:00Z"), new Date("2026-01-15T03:00:00Z"))).toBe(true);
    expect(isSameAppDay(new Date("2026-01-14T21:30:00Z"), new Date("2026-01-14T06:00:00Z"))).toBe(false);
  });

  it("Pazar gecesi o haftanin Pazartesi'sine duser", () => {
    // 2026-01-11 Pazar 23:30 Istanbul = 2026-01-11T20:30:00Z
    expect(appWeekStartKey(new Date("2026-01-11T20:30:00Z"))).toBe("2026-01-05");
    // Pazartesi gununun kendisi o hafta baslar.
    expect(appWeekStartKey(new Date("2026-01-12T08:00:00Z"))).toBe("2026-01-12");
    // Cumartesi -> ayni haftanin Pazartesi'si.
    expect(appWeekStartKey(new Date("2026-01-17T12:00:00Z"))).toBe("2026-01-12");
  });

  it("appWeekKeys Pazartesi'den baslayan 7 gun doner", () => {
    expect(appWeekKeys(new Date("2026-01-14T21:30:00Z"))).toEqual([
      "2026-01-12",
      "2026-01-13",
      "2026-01-14",
      "2026-01-15",
      "2026-01-16",
      "2026-01-17",
      "2026-01-18",
    ]);
  });

  it("todayKey ve tomorrowKey takvim gunu farki 1'dir", () => {
    expect(daysBetween(todayKey(), tomorrowKey())).toBe(1);
  });

  it("daysBetween takvim gunleri uzerinden hesap yapar", () => {
    expect(daysBetween("2026-01-11", "2026-01-14")).toBe(3);
    expect(daysBetween("2026-01-14", "2026-01-11")).toBe(-3);
    expect(daysBetween("2026-01-14", "2026-01-14")).toBe(0);
  });

  it("addAppDays ve appDayUtc takvim gunu aritmetigini tz bagimsiz yapar", () => {
    const monday = keyToUtc("2026-01-12");
    expect(addAppDays(monday, 6).toISOString().slice(0, 10)).toBe("2026-01-18");
    expect(appDayUtc(new Date("2026-01-14T21:30:00Z")).toISOString().slice(0, 10)).toBe("2026-01-15");
  });

  it("appLocalToUtc yerel gun+saati ISO UTC'ye cevirir (sabit offset yok)", () => {
    expect(appLocalToUtc("2026-08-30", 14, 0)).toBe("2026-08-30T11:00:00.000Z");
    expect(appLocalToUtc("2026-08-30", 23, 59)).toBe("2026-08-30T20:59:00.000Z");
    expect(appLocalToUtc("2026-08-30", 0, 30)).toBe("2026-08-29T21:30:00.000Z");
  });

  it("appTimeParts app saat diliminde saat/dakika verir", () => {
    // 21:30 UTC = Istanbul 00:30 (ertesi gun).
    expect(appTimeParts(new Date("2026-01-14T21:30:00Z"))).toEqual({ hour: 0, minute: 30 });
    // 12:00 UTC = Istanbul 15:00.
    expect(appTimeParts(new Date("2026-01-14T12:00:00Z"))).toEqual({ hour: 15, minute: 0 });
  });

  it("datetime-local degerini tarayici saat diliminden bagimsiz app saatine cevirir", () => {
    expect(appDateTimeInputValue("2026-08-30T11:00:00.000Z")).toBe("2026-08-30T14:00");
    expect(appDateTimeInputToUtc("2026-08-30T14:00")).toBe("2026-08-30T11:00:00.000Z");
    expect(appDateTimeInputToUtc("")).toBeUndefined();
  });
});
