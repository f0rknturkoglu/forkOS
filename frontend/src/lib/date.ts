/**
 * Ortak tarih/saat sözleşmesi (Faz 14).
 *
 * Uygulama günü kavramı TEK kaynaktan gelir: `APP_TIME_ZONE`
 * (Europe/Istanbul) — backend `settings.timezone` ile aynı. Tarayıcının
 * yerel saatine göre gün kararı VEREN kod bu modüle taşınmalıdır;
 * `dateUsage.test.ts` bunu korur. Gösterim amaçlı `toLocaleDateString()`
 * kullanımı serbesttir.
 *
 * Gün anahtarı "YYYY-MM-DD" (app tz). Gün aritmetiği UTC-projekte edilmiş
 * `Date`'lerle yapılır: `keyToUtc` bir anahtarı UTC gece yarısı olarak
 * temsil eder, böylece yaz saati / tarayıcı diliminden bağımsız kalır.
 */
const APP_TIME_ZONE = "Europe/Istanbul";

export function localDateKey(value: Date, timeZone = APP_TIME_ZONE): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(value);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

/** "Bugün"ün (app tz) gün anahtarı. */
export function todayKey(timeZone = APP_TIME_ZONE): string {
  return localDateKey(new Date(), timeZone);
}

/** "Yarın"ın (app tz) gün anahtarı. */
export function tomorrowKey(timeZone = APP_TIME_ZONE): string {
  return localDateKey(new Date(Date.now() + 86_400_000), timeZone);
}

/** İki an aynı uygulama gününde mi? */
export function isSameAppDay(a: Date, b: Date, timeZone = APP_TIME_ZONE): boolean {
  return localDateKey(a, timeZone) === localDateKey(b, timeZone);
}

/** "YYYY-MM-DD" anahtarını UTC gece yarısı olarak temsil eden Date. */
export function keyToUtc(key: string): Date {
  const [year, month, day] = key.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

/** Bir anın app gününü UTC gece yarısı olarak temsil eden Date. */
export function appDayUtc(value: Date, timeZone = APP_TIME_ZONE): Date {
  return keyToUtc(localDateKey(value, timeZone));
}

/** İki gün anahtarı arasındaki takvim günü farkı: toKey - fromKey. */
export function daysBetween(fromKey: string, toKey: string): number {
  const from = keyToUtc(fromKey);
  const to = keyToUtc(toKey);
  return Math.round((to.getTime() - from.getTime()) / 86_400_000);
}

/** Anın içinde bulunduğu app haftasının Pazartesi anahtarı (Pazar -> o hafta Pzt). */
export function appWeekStartKey(value = new Date(), timeZone = APP_TIME_ZONE): string {
  const day = keyToUtc(localDateKey(value, timeZone));
  const dow = day.getUTCDay(); // 0 = Pazar
  const diff = (dow + 6) % 7;
  return new Date(Date.UTC(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate() - diff))
    .toISOString()
    .slice(0, 10);
}

/** Pazartesi'den başlayan 7 günlük app haftasının anahtarları. */
export function appWeekKeys(value = new Date(), timeZone = APP_TIME_ZONE): string[] {
  const start = keyToUtc(appWeekStartKey(value, timeZone));
  return Array.from({ length: 7 }, (_, i) =>
    new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), start.getUTCDate() + i)).toISOString().slice(0, 10),
  );
}

/** App gününe `count` takvim günü ekler, UTC-projekte günü döndürür. */
export function addAppDays(value: Date, count: number, timeZone = APP_TIME_ZONE): Date {
  const day = keyToUtc(localDateKey(value, timeZone));
  return new Date(Date.UTC(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate() + count));
}

/** Anın app saat dilimindeki saat/dakika parçaları. */
export function appTimeParts(value: Date, timeZone = APP_TIME_ZONE): { hour: number; minute: number } {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(value);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return { hour: Number(values.hour) % 24, minute: Number(values.minute) };
}

/** Bir ISO ani datetime-local kontrolunde app saat dilimiyle gosterir. */
export function appDateTimeInputValue(value: string | Date, timeZone = APP_TIME_ZONE): string {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const { hour, minute } = appTimeParts(date, timeZone);
  return `${localDateKey(date, timeZone)}T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

/** datetime-local wall time degerini app saat dilimindeki UTC anina cevirir. */
export function appDateTimeInputToUtc(value: string, timeZone = APP_TIME_ZONE): string | undefined {
  if (!value) return undefined;
  const match = value.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})$/);
  if (!match) return undefined;
  const [, dayKey, rawHour, rawMinute] = match;
  const hour = Number(rawHour);
  const minute = Number(rawMinute);
  const projected = keyToUtc(dayKey);
  if (
    Number.isNaN(projected.getTime()) ||
    projected.toISOString().slice(0, 10) !== dayKey ||
    hour < 0 ||
    hour > 23 ||
    minute < 0 ||
    minute > 59
  ) {
    return undefined;
  }
  return appLocalToUtc(dayKey, hour, minute, timeZone);
}

/** App tz'deki yerel gun+saati ISO UTC'ye cevirir (Faz 30).
 *
 * Sabit offset yok: UTC adayini saat saat geriye tarayip app wall time'ina
 * eslesen ani bulur (Faz 14 helper'larinin tersi). Parser due_at gibi
 * kararlar buradan gecer.
 */
export function appLocalToUtc(dayKey: string, hour: number, minute: number, timeZone = APP_TIME_ZONE): string {
  const day = keyToUtc(dayKey);
  let candidate = new Date(Date.UTC(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate(), hour, minute));
  for (let i = 0; i < 25; i++) {
    const parts = appTimeParts(candidate, timeZone);
    if (localDateKey(candidate, timeZone) === dayKey && parts.hour === hour && parts.minute === minute) {
      return candidate.toISOString();
    }
    candidate = new Date(candidate.getTime() - 3_600_000);
  }
  return candidate.toISOString();
}

/** ISO ani tr-TR yerel tarih olarak bicimlendirir (gorunum amacli). */
export function formatTrDate(value: string | Date, options?: Intl.DateTimeFormatOptions): string {
  const date = value instanceof Date ? value : new Date(value);
  return date.toLocaleDateString("tr-TR", options);
}

/** ISO ani tr-TR yerel tarih+saat olarak bicimlendirir (gorunum amacli). */
export function formatTrDateTime(value: string | Date, options?: Intl.DateTimeFormatOptions): string {
  const date = value instanceof Date ? value : new Date(value);
  return date.toLocaleString("tr-TR", options);
}
