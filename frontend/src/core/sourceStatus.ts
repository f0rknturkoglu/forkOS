/**
 * Kaynak/koşu/besleme durumlarının TEK anlam kaynağı.
 *
 * Neden: aynı durum sözlüğü beş yerde tekrar ediyordu (SourceHealthPage,
 * SourcesWorkspace, SyncProgress, StatusLed, widget'lar) ve her kopya
 * farklı bir ton/label seçiyordu. Burada tek tablo var; yüzeyler yalnız
 * `label` + `tone` + `attention` okur.
 *
 * SINIR: sağlık EŞİKLERİ burada ÜRETİLMEZ. "Sorun mu?" kararı backend'in
 * özetinden gelir (`/sources/coverage`: `circuit_open`, `last_status`,
 * `consecutive_empty`, `last_error_kind`) ve `isProblem()` yalnız o alanları
 * okur. İstemci son N koşuyu dilimleyip kendi eşiğini hesaplamaz.
 *
 * Dürüstlük kuralı: `disabled` bir hata DEĞİLDİR (kapalı feed, kapalı worker,
 * kapalı H6). `unknown` asla yeşil gösterilmez.
 */
import type { ChipTone } from "./ui";

/** Chip tonlarıyla aynı küme (Core UI ile tek sözlük). */
export type StatusTone = Extract<ChipTone, "ok" | "warn" | "danger" | "accent" | "neutral">;

export interface StatusView {
  /** Kullanıcıya gösterilen Türkçe etiket; ham enum kullanıcıya çıkmaz. */
  label: string;
  tone: StatusTone;
  /** true → "ilgi isteyen" sayılır (kırmızı/amber problem). */
  attention: boolean;
}

/**
 * Koşu/durum sözlüğü. Backend `source_run.status` kümesi + arayüzün ayırt
 * etmesi gereken iki ek hâl: `new` (hiç çalışmadı) ve `unknown` (bilinmiyor).
 */
type RunState =
  "ok" | "empty" | "partial" | "error" | "running" | "queued" | "abandoned" | "disabled" | "new" | "unknown";

const RUN_STATES: Record<RunState, StatusView> = {
  ok: { label: "sağlıklı", tone: "ok", attention: false },
  // Tek boş koşu "sorun" değildir; üst üste üç boşkoşu `isProblem()` ile
  // ayrıca işaretlenir (bkz. consecutive_empty). Bu yüzden attention=false.
  empty: { label: "yeni kayıt yok", tone: "warn", attention: false },
  partial: { label: "kısmi", tone: "warn", attention: true },
  error: { label: "hata", tone: "danger", attention: true },
  running: { label: "çekiliyor", tone: "accent", attention: false },
  queued: { label: "sırada", tone: "neutral", attention: false },
  abandoned: { label: "yarım kaldı", tone: "warn", attention: true },
  // Kullanıcının BİLEREK kapattığı şey kırmızı gösterilmez.
  disabled: { label: "kapalı", tone: "neutral", attention: false },
  new: { label: "hiç çalışmadı", tone: "neutral", attention: false },
  unknown: { label: "bilinmiyor", tone: "neutral", attention: false },
};

/** Bilinmeyen bir durum gelirse yalan söyleme: `unknown` göster. */
export function runStateView(state: string | null | undefined): StatusView {
  if (!state) return RUN_STATES.unknown;
  return RUN_STATES[state as RunState] ?? { label: state, tone: "neutral", attention: false };
}

/** Devre kesici göstergesi (chip olarak sağda durur). */
export function circuitView(open: boolean | null | undefined): StatusView | null {
  if (!open) return null;
  return { label: "devre açık", tone: "danger", attention: true };
}

/** Backend sağlık sinyalleri — `/sources/coverage` satırının ilgili alanları. */
interface ProblemSignals {
  circuit_open?: boolean | null;
  last_status?: string | null;
  consecutive_empty?: number | null;
  last_error_kind?: string | null;
}

/** Üst üste kaç boş koşu "sessiz ölüm" sayılır (backend ile aynı eşik). */
export const SILENT_EMPTY_THRESHOLD = 3;

/**
 * Sorun mu? Eşikler backend sözleşmesidir: devre açık, son koşu hata, ya da
 * üst üste `SILENT_EMPTY_THRESHOLD` boş koşu.
 */
export function isProblem(signals: ProblemSignals | null | undefined): boolean {
  if (!signals) return false;
  if (signals.circuit_open) return true;
  if (signals.last_status === "error") return true;
  return (signals.consecutive_empty ?? 0) >= SILENT_EMPTY_THRESHOLD;
}

/** Sorunun nedeni, insan diliyle (attention satırında gösterilir). */
export function problemReasons(signals: ProblemSignals | null | undefined): string[] {
  if (!signals) return [];
  const reasons: string[] = [];
  if (signals.circuit_open) reasons.push("devre açık");
  if (signals.last_status === "error") {
    const kind = errorKindLabel(signals.last_error_kind);
    reasons.push(kind ? `son koşu hata (${kind})` : "son koşu hata");
  }
  const empty = signals.consecutive_empty ?? 0;
  if (empty >= SILENT_EMPTY_THRESHOLD) reasons.push(`${empty} koşum boş`);
  return reasons;
}

/**
 * Hata sınıfı etiketi. Ham enum kullanıcıya çıkmaz; kısa ve okunaklı karşılığı
 * gösterilir ("http_429" → "429"). Bilinmeyen sınıf varsa olduğu gibi kalır —
 * uydurma bir etiket üretilmez.
 */
const ERROR_KIND_LABELS: Record<string, string> = {
  tls: "TLS",
  dns: "DNS",
  timeout: "zaman aşımı",
  http_403: "403",
  http_404: "404",
  http_429: "429",
  http_5xx: "5xx",
  parser: "ayrıştırma",
  partial: "kısmi",
  circuit_open: "devre açık",
  unknown: "bilinmiyor",
};

export function errorKindLabel(kind: string | null | undefined): string | null {
  if (!kind) return null;
  return ERROR_KIND_LABELS[kind] ?? kind;
}

/** Hata sınıfı tonu: "yine denenebilir" sınıflar amber, kalıcı olanlar kırmızı. */
export function errorKindTone(kind: string | null | undefined): StatusTone {
  if (!kind) return "neutral";
  if (kind === "http_429" || kind === "http_5xx" || kind === "timeout" || kind === "dns" || kind === "tls") {
    return "warn";
  }
  if (kind === "circuit_open" || kind === "parser") return "danger";
  return "warn";
}

/** Kaynak sınıfı (katalog `class` alanı). */
const CLASS_LABELS: Record<string, string> = {
  critical: "Kritik",
  normal: "Normal",
  slow_optin: "Yavaş / isteğe bağlı",
};

export function sourceClassLabel(sourceClass: string | null | undefined): string | null {
  if (!sourceClass) return null;
  return CLASS_LABELS[sourceClass] ?? sourceClass;
}

/** Kaynak türü (katalog `kind` alanı). */
const KIND_LABELS: Record<string, string> = { job: "İş ilanı", announcement: "Duyuru" };

export function sourceKindLabel(kind: string | null | undefined): string | null {
  if (!kind) return null;
  return KIND_LABELS[kind] ?? kind;
}

/** RSS besleme durumu: `active=false` KAPALI'dır, bozuk değildir. (Dosya ici tip.) */
interface FeedSignals {
  active: boolean;
  error_count?: number | null;
  last_status?: string | null;
  last_fetched_at?: string | null;
}

export function feedStateView(feed: FeedSignals | null | undefined): StatusView {
  if (!feed) return RUN_STATES.unknown;
  if (!feed.active) return { label: "kapalı", tone: "neutral", attention: false };
  if ((feed.error_count ?? 0) > 0) {
    return { label: `${feed.error_count} hata`, tone: "danger", attention: true };
  }
  if (!feed.last_fetched_at) return { label: "çekilmedi", tone: "neutral", attention: false };
  if (feed.last_status === "empty") return { label: "yeni kayıt yok", tone: "warn", attention: false };
  return RUN_STATES.ok;
}

/**
 * Toplu sağlık cümlesi: yeşil kutuyu YALNIZ gerçekten bilinen ve temiz bir
 * durumda üretir. `unknown` true ise cümle "bilinmiyor" der.
 */
export interface HealthCounts {
  total: number;
  healthy: number;
  attention: number;
  unknown?: boolean;
}

export function healthSummaryLabel(counts: HealthCounts): string {
  if (counts.unknown) return "durum bilinmiyor";
  if (counts.total === 0) return "kayıt yok";
  if (counts.attention === 0) return `${counts.healthy} sağlıklı`;
  return `${counts.healthy} sağlıklı · ${counts.attention} ilgi istiyor`;
}

/** Genel (overall) durum: skor değil, betimleyici. */
type OverallState = "healthy" | "attention" | "partly_unknown";

const OVERALL: Record<OverallState, StatusView> = {
  healthy: { label: "Sağlıklı", tone: "ok", attention: false },
  attention: { label: "İlgi gerekiyor", tone: "warn", attention: true },
  partly_unknown: { label: "Durum kısmen bilinmiyor", tone: "neutral", attention: false },
};

export function overallView(state: OverallState): StatusView {
  return OVERALL[state];
}

/**
 * Genel durum: bir alt sistem bilinmiyorsa "sağlıklı" DENMEZ (§33).
 * Sıra: bilinmeyen > sorun > sağlıklı.
 */
export function overallState(input: { unknown: boolean; attention: boolean }): OverallState {
  if (input.attention) return "attention";
  if (input.unknown) return "partly_unknown";
  return "healthy";
}

/**
 * Liste görünümü için hata metni önizlemesi (§66).
 *
 * Kural: liste tek/iki satırlık sınırlı bir önizleme gösterir; TAM (maskelenmiş)
 * metin satırın `title`ında, kapsam matrisinde ve kopyalanan tanılama paketinde
 * kalır. Ayrıca kullanıcıya dönük metinden `ConnectError:` gibi sınıf ön eki
 * atılır — tanılamada bu bilgi zaten tam hâliyle durur.
 */
export function errorPreview(text: string | null | undefined, max = 140): string | null {
  if (!text) return null;
  const collapsed = text.replace(/\s+/g, " ").trim();
  const withoutClass = collapsed.replace(/^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception|Warning):\s*/, "");
  const clean = withoutClass || collapsed;
  if (!clean) return null;
  return clean.length > max ? `${clean.slice(0, max - 1)}…` : clean;
}
