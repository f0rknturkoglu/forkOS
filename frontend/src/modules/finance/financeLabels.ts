import {
  Briefcase,
  Car,
  Clapperboard,
  Gift,
  GraduationCap,
  HeartPulse,
  Home,
  Laptop,
  RotateCw,
  Tag,
  TrendingUp,
  UtensilsCrossed,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Finans modulunun gorunum sozlugu: Turkce etiketler, para bicimi, marka rengi.
 *
 * Backend kategori/marka alanlarini SERBEST metin tutar; burasi yalnizca
 * gosterimi cevirir. Bilinmeyen bir kategori ya da marka gelirse kirilmaz,
 * ham degeriyle (ve turetilmis bir renkle) gorunur.
 */

export const EXPENSE_CATEGORIES = [
  "food",
  "rent",
  "bills",
  "transport",
  "subscriptions",
  "shopping",
  "health",
  "education",
  "entertainment",
  "other",
] as const;

export const INCOME_CATEGORIES = ["salary", "freelance", "investment", "gift", "other"] as const;

const CATEGORY_LABELS: Record<string, string> = {
  food: "Market",
  rent: "Kira",
  bills: "Fatura",
  transport: "Ulaşım",
  subscriptions: "Abonelik",
  shopping: "Alışveriş",
  health: "Sağlık",
  education: "Eğitim",
  entertainment: "Eğlence",
  salary: "Maaş",
  freelance: "Serbest çalışma",
  investment: "Yatırım",
  gift: "Hediye",
  other: "Diğer",
};

export const categoryLabel = (value: string): string => CATEGORY_LABELS[value] ?? value;

/* Kategori ikonlari: listede her satirin solunda yuvarlak rozet icinde
   gorunur. Bilinmeyen kategori "Tag" ile cizilir -- backend serbest metin
   tutar, arayuz kirilmaz. */
const CATEGORY_ICONS: Record<string, LucideIcon> = {
  food: UtensilsCrossed,
  rent: Home,
  bills: Zap,
  transport: Car,
  subscriptions: RotateCw,
  shopping: Tag,
  health: HeartPulse,
  education: GraduationCap,
  entertainment: Clapperboard,
  salary: Briefcase,
  freelance: Laptop,
  investment: TrendingUp,
  gift: Gift,
  other: Tag,
};

export const categoryIcon = (value: string): LucideIcon => CATEGORY_ICONS[value] ?? Tag;

export const FREQUENCIES = ["monthly", "quarterly", "yearly"] as const;

const FREQUENCY_LABELS: Record<string, string> = {
  monthly: "Aylık",
  quarterly: "3 aylık",
  yearly: "Yıllık",
};

export const frequencyLabel = (value: string): string => FREQUENCY_LABELS[value] ?? value;

/** Siklik -> ay sayisi (backend MONTHS_PER_PERIOD ile ayni sozlesme). */
const MONTHS_PER_PERIOD: Record<string, number> = { monthly: 1, quarterly: 3, yearly: 12 };

/** Tekrarlayan odemenin bir aya dusen payi: yillik 1200 -> 100. */
export function monthlyShare(amount: number | string, frequency: string): number {
  const months = MONTHS_PER_PERIOD[frequency] ?? 1;
  return Number(amount) / months;
}

/* Turkce sira eki, son rakama gore (1'i, 2'si, 3'u, 6'si...). 10/20/30 onluk
   okunusuyla ayrisir: "10'u", "20'si", "30'u". */
const DAY_SUFFIX = ["", "i", "si", "ü", "ü", "i", "sı", "si", "i", "u"];
const TENS_SUFFIX: Record<number, string> = { 10: "u", 20: "si", 30: "u" };

/** 15 -> "15’i", 20 -> "20’si", 3 -> "3’ü" */
export function dayOrdinal(day: number): string {
  const suffix = day % 10 === 0 ? (TENS_SUFFIX[day] ?? "u") : DAY_SUFFIX[day % 10];
  return `${day}’${suffix}`;
}

/** Odeme ritmi tek cumlede: "her ayın 15’i", "yılda bir, ayın 20’si". */
export function billingLabel(frequency: string, billingDay: number | null): string {
  if (!billingDay) return frequencyLabel(frequency);
  const day = dayOrdinal(billingDay);
  if (frequency === "monthly") return `her ayın ${day}`;
  if (frequency === "quarterly") return `3 ayda bir, ayın ${day}`;
  if (frequency === "yearly") return `yılda bir, ayın ${day}`;
  return `${frequencyLabel(frequency)} · ayın ${day}`;
}

/* ── Marka rozetleri ──────────────────────────────────────────────────
   Abonelik adindan slug uretilir; kullaniciya marka SECTIRILMEZ. "Netflix"
   yazmak yeterli. Renk, bilinen markalarda sabit; digerlerinde slug'dan
   turetilir -- ayni ad her zaman ayni rengi alir.
   Renkler tema tokenlarindan (--chart-N); JSX'e sabit hex yazilmaz. */

const CHART_TOKENS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--chart-6)",
  "var(--chart-7)",
  "var(--chart-8)",
] as const;

/** Bilinen markalarin sabit palet indeksi (0-7). */
const BRAND_TONE: Record<string, number> = {
  netflix: 2,
  youtube: 2,
  spotify: 1,
  amazon_prime: 3,
  icloud: 0,
  wow: 4,
  disney_plus: 0,
  chatgpt: 5,
};

/** Baslik -> backend'in kabul ettigi slug ([a-z0-9_], en fazla 32). */
export function subSlug(title: string): string | null {
  const slug = title
    .toLocaleLowerCase("tr")
    .replace(/ı/g, "i")
    .replace(/ş/g, "s")
    .replace(/ğ/g, "g")
    .replace(/ü/g, "u")
    .replace(/ö/g, "o")
    .replace(/ç/g, "c")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 32)
    .replace(/_+$/, "");
  return slug || null;
}

/** Slug'in sabit palet rengi. Bilinmeyen marka da her seferinde ayni rengi alir. */
export function subColor(sub: string | null): string {
  if (!sub) return "var(--chart-1)";
  const tone = BRAND_TONE[sub];
  if (tone !== undefined) return CHART_TOKENS[tone];
  let hash = 0;
  for (const char of sub) hash = (hash * 31 + char.charCodeAt(0)) % 997;
  return CHART_TOKENS[hash % CHART_TOKENS.length];
}

export const colorOf = (index: number): string => CHART_TOKENS[index % CHART_TOKENS.length];

/* ── Para ─────────────────────────────────────────────────────────── */

/** Tutari tr-TR bicimiyle yazar. Gecersiz kur kodunda sayi + kod'a duser. */
export function money(value: number | string, currency: string, fractions = 2): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";
  try {
    return new Intl.NumberFormat("tr-TR", {
      style: "currency",
      currency: currency.trim().toUpperCase(),
      minimumFractionDigits: fractions,
      maximumFractionDigits: fractions,
    }).format(amount);
  } catch {
    return `${amount.toLocaleString("tr-TR", { maximumFractionDigits: fractions })} ${currency.trim()}`;
  }
}

/** Dilim payi: 0.866 -> "%86,6". Donut merkezinde kullanilir. */
export function percent(ratio: number): string {
  if (!Number.isFinite(ratio)) return "—";
  return new Intl.NumberFormat("tr-TR", { style: "percent", maximumFractionDigits: 1 }).format(ratio);
}

/** Ozet seridi icin kurussuz kisa bicim. */
export const moneyShort = (value: number | string, currency: string): string => money(value, currency, 0);

/** İşaretli net: +/- her zaman görünür. */
export function signedMoney(value: number | string, currency: string): string {
  const amount = Number(value);
  const text = moneyShort(Math.abs(amount), currency);
  if (amount === 0) return text;
  return `${amount > 0 ? "+" : "−"}${text}`;
}

/* ── Ay gezinme ───────────────────────────────────────────────────── */

/** "YYYY-MM" -> { year, month } */
export function parseMonth(key: string): { year: number; month: number } {
  const [year, month] = key.split("-").map(Number);
  return { year, month };
}

export const monthKeyOf = (dayKey: string): string => dayKey.slice(0, 7);

/** Ay anahtarini `delta` ay kaydirir (yil sinirini asar). */
export function shiftMonth(key: string, delta: number): string {
  const { year, month } = parseMonth(key);
  const index = year * 12 + (month - 1) + delta;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}`;
}

/** "2026-08" -> "Ağustos 2026" */
export function monthLabel(key: string): string {
  const { year, month } = parseMonth(key);
  const label = new Intl.DateTimeFormat("tr-TR", { month: "long", year: "numeric" }).format(
    new Date(Date.UTC(year, month - 1, 1)),
  );
  return label.charAt(0).toLocaleUpperCase("tr") + label.slice(1);
}

/** "2026-08" -> "Ağu" -- grafik eksen etiketi (yil bilinir, ay kisaltilir). */
export function monthShort(key: string): string {
  const { year, month } = parseMonth(key);
  return new Intl.DateTimeFormat("tr-TR", { month: "short" })
    .format(new Date(Date.UTC(year, month - 1, 1)))
    .replace(/\.$/, "");
}

/** "2026-08-26" -> "26 Ağustos Çarşamba" */
export function dayLabel(dayKey: string): string {
  const [year, month, day] = dayKey.split("-").map(Number);
  return new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long", weekday: "long" }).format(
    new Date(Date.UTC(year, month - 1, day)),
  );
}

/** Vade uzakligi: "bugün", "yarın", "3 gün sonra", "2 gün gecikti". */
export function dueLabel(days: number): string {
  if (days === 0) return "bugün";
  if (days === 1) return "yarın";
  if (days === -1) return "dün gecikti";
  return days > 0 ? `${days} gün sonra` : `${Math.abs(days)} gün gecikti`;
}
