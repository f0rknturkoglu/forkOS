/**
 * Yerel Turkce tarih/gorev ayristirici (Faz 23).
 *
 * Saf ve yan etkisizdir: network yok, LLM yok. Cikti ONERIDIR -- kullanici
 * duzenlemeden kayit olusturulmaz. Plan (`plan_day`) ile son tarih
 * (`due_at`) BIRBIRINE CEVRILMEZ: "bugun" plan anlamina gelir, "bugun
 * teslim" / "son tarih bugun" due anlamina.
 *
 * Gun anahtarlari Faz 14 ortak helper'larindan (Europe/Istanbul) gelir.
 */
import { addAppDays, appLocalToUtc, appWeekStartKey, keyToUtc, localDateKey, todayKey } from "./date";

interface ParseResult {
  /** Temizlenmis baslik: tuketilen parcalar cikarilmis. */
  title: string;
  /** Onerilen plan gunu (app tz anahtari). */
  plan_day?: string;
  /** Onerilen son tarih (ISO; "teslim" ifadelerinden). */
  due_at?: string;
  /** Onerilen saat "HH:MM". */
  time?: string;
  priority?: number;
  tags: string[];
  /** Belirsizlik / varsayim uyarilari. */
  warnings: string[];
  /** Metinden tuketilen parcalar (UI gosterimi). */
  consumed: string[];
}

const WEEKDAYS: Record<string, number> = {
  pazar: 0,
  pazartesi: 1,
  salı: 2,
  sali: 2,
  çarşamba: 3,
  carsamba: 3,
  perşembe: 4,
  persembe: 4,
  cuma: 5,
  cumartesi: 6,
};

const PRIORITY_PATTERNS: [RegExp, number, string][] = [
  [/yüksek öncelik|öncelik yüksek|yuksek oncelik|oncelik yuksek|acil/i, 3, "yüksek öncelik"],
  [/düşük öncelik|dusuk oncelik|öncelik düşük|oncelik dusuk/i, 1, "düşük öncelik"],
];

const TIME_PATTERN = /\b(\d{1,2})[:.](\d{2})\b/;
const MONTH_DAY_PATTERN = /ay[ıi]n\s+(\d{1,2})(?:'?\w*)?/i;
const NEXT_WEEK_PATTERN = /gelecek hafta/i;
const DEADLINE_PATTERNS: RegExp[] = [
  /son tarih\s+(bugün|yarın|pazartesi|salı|sali|çarşamba|carsamba|perşembe|persembe|cuma|cumartesi|pazar|gelecek hafta|ay[ıi]n\s+\d{1,2})/i,
  /(bugün|yarın|pazartesi|salı|sali|çarşamba|carsamba|perşembe|persembe|cuma|cumartesi|pazar)\s+teslim/i,
];

function tr(value: string): string {
  return value.toLocaleLowerCase("tr-TR");
}

function dayKeyForToken(token: string, now: Date): { day: string; warning?: string } {
  const lower = tr(token.trim());
  if (lower === "bugün" || lower === "bugun") return { day: localDateKey(now) };
  if (lower === "yarın" || lower === "yarin") return { day: localDateKey(addAppDays(now, 1)) };
  if (NEXT_WEEK_PATTERN.test(lower)) {
    // "gelecek hafta": one sonraki haftanin Pazartesi'si (varsayim + uyari).
    const nextMonday = addAppDays(keyToUtc(appWeekStartKey(now)), 7);
    return { day: localDateKey(nextMonday), warning: "gelecek hafta pazartesine planlandı" };
  }
  if (WEEKDAYS[lower] !== undefined) {
    // Gun adi hesabi VERILEN `now`'dan (real sistem gunu degil -- Faz 30).
    const todayDow = keyToUtc(localDateKey(now)).getUTCDay();
    const targetDow = WEEKDAYS[lower];
    let diff = targetDow - todayDow;
    if (diff < 0) diff += 7;
    // Bugunku gun adi verildiyse bugun anlamina gelir (hizli yakalama).
    return { day: localDateKey(addAppDays(now, diff)) };
  }
  const monthDay = lower.match(MONTH_DAY_PATTERN);
  if (monthDay) {
    const day = Number(monthDay[1]);
    const today = keyToUtc(localDateKey(now));
    const year = today.getUTCFullYear();
    let month = today.getUTCMonth();
    const daysInMonth = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
    const monthBumped = day < today.getUTCDate() || day > daysInMonth;
    if (monthBumped) month += 1;
    // Kisa ay: gecersiz gun SESSIZCE baska aya tasmaz -- ya gercek gunun
    // gelecek ayine gidilir (uyari ile) ya da ay sonuna kirpilir (uyari ile).
    const targetDays = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
    if (day > targetDays) {
      return {
        day: localDateKey(new Date(Date.UTC(year, month, targetDays))),
        warning: `ayın ${day}'i bu ay yok — ay sonuna (${targetDays}) alındı`,
      };
    }
    if (monthBumped && day > daysInMonth) {
      return {
        day: localDateKey(new Date(Date.UTC(year, month, day))),
        warning: `ayın ${day}'i bu ay yok — gelecek ayın ${day}'ine alındı`,
      };
    }
    return { day: localDateKey(new Date(Date.UTC(year, month, day))) };
  }
  return { day: todayKey(), warning: "tarih çözülemedi" };
}

/**
 * Metni ayristirir. Tuketilen parcalar basliktan cikarilir; oneriler
 * uyari etiketleriyle birlikte doner. Network cagrisi YOKTUR.
 */
export function parseTaskText(raw: string, now = new Date()): ParseResult {
  const tags: string[] = [];
  let text = raw;
  const consumed: string[] = [];
  const warnings: string[] = [];
  let priority: number | undefined;
  let time: string | undefined;
  let plan_day: string | undefined;
  let due_at: string | undefined;

  // Etiketler.
  text = text.replace(/#([\p{L}\p{N}_-]+)/gu, (full, tag: string) => {
    tags.push(tag);
    consumed.push(full);
    return " ";
  });

  // Oncelik.
  for (const [pattern, value, label] of PRIORITY_PATTERNS) {
    if (pattern.test(text)) {
      priority = value;
      text = text.replace(pattern, " ");
      consumed.push(label);
      break;
    }
  }

  // Saat.
  const timeMatch = text.match(TIME_PATTERN);
  if (timeMatch) {
    time = `${timeMatch[1].padStart(2, "0")}:${timeMatch[2]}`;
    text = text.replace(TIME_PATTERN, " ");
    consumed.push(timeMatch[0]);
  }

  // Son tarih ifadeleri: "son tarih X" / "X teslim" -> due_at (plan degil).
  for (const pattern of DEADLINE_PATTERNS) {
    const match = text.match(pattern);
    if (match) {
      const token = match[1];
      const { day, warning } = dayKeyForToken(token, now);
      if (warning) warnings.push(warning);
      const [hour, minute] = time ? time.split(":").map(Number) : [23, 59];
      // App tz'deki yerel gun+saat -> ISO UTC (sabit offset yok, Faz 30).
      due_at = appLocalToUtc(day, hour, minute);
      consumed.push(match[0]);
      text = text.replace(pattern, " ");
      break;
    }
  }

  // Gun token'lari -> plan_day (onceki adimda tuketilmediyse).
  const dayTokens = text.match(
    /(bugün|bugun|yarın|yarin|gelecek hafta|pazartesi|salı|sali|çarşamba|carsamba|perşembe|persembe|cuma|cumartesi|pazar|ay[ıi]n\s+\d{1,2})/gi,
  );
  if (dayTokens) {
    const token = dayTokens[0];
    const { day, warning } = dayKeyForToken(token, now);
    if (warning) warnings.push(warning);
    plan_day = day;
    consumed.push(token);
    text = text.replace(new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"), " ");
  }

  const title = text.replace(/\s+/g, " ").trim();
  return { title, plan_day, due_at, time, priority, tags, warnings, consumed };
}
