import type { ReviewPreview } from "@/core/types";

/** Dönem özetindeki üst düzey sinyal. Sayı kutusu istenirse bağlantı olur. */
interface ReviewMetricRow {
  label: string;
  value: string | number;
  hint?: string;
  href?: string;
}

/**
 * Dönem özeti: EN FAZLA dört sinyal.
 *
 * Değerlendirme bir analitik panosu değil, kapanış anıdır; bu yüzden burada
 * yalnız dönemin emeğini ve devreden yükü taşıyan sayılar durur. Kalan
 * kırılımlar ikincil katlanır ayrıntıya ya da kendi modüllerine (Etkinlik,
 * Kariyer, Öğrenme) aittir.
 */
export function reviewMetricRows(data: ReviewPreview): ReviewMetricRow[] {
  const stats = data.stats;
  return [
    { label: "Tamamlanan iş", value: stats.todos.completed },
    { label: "Odak süresi", value: `${stats.focus.minutes} dk`, hint: `${stats.focus.sessions} seans` },
    { label: "Aktif gün", value: stats.focus.active_days },
    // Devreden yük karar bekleyen işi gösterir; tıklanınca görev listesine
    // gider, çünkü tek gerçek eylem orada.
    { label: "Devreden açık görev", value: data.unfinished_todos.length, href: "#/todos" },
  ];
}

/** İkincil sinyal: katlanır ayrıntıda ya da ajan paketinde görünür. */
interface ReviewSignal {
  label: string;
  value: number;
  unit?: string;
}

/**
 * İkincil sinyaller (üst düzey özetin dışında kalanlar).
 *
 * Kariyer/öğrenme kırılımları buraya girmez: kendi sayfaları zaten sahibi.
 */
export function reviewSecondarySignals(stats: ReviewPreview["stats"]): ReviewSignal[] {
  return [
    { label: "Kart tekrarı", value: stats.flashcards.reviewed },
    {
      label: "Rutin tamamlama",
      value: Object.values(stats.habits).reduce((total, value) => total + value, 0),
    },
    { label: "Yeni not", value: stats.capture.notes },
    { label: "Kaydedilen kaynak", value: stats.capture.bookmarks },
    { label: "Okunan RSS", value: stats.capture.rss_read },
    { label: "GitHub commit", value: stats.github.commits },
    { label: "En uzun odak", value: stats.focus.longest_session, unit: "dk" },
    { label: "Yarıda kesilen", value: stats.focus.interrupted },
  ];
}

/** Kayıtlı bir değerlendirmenin `stats` JSON'undan sayısal alan okur. */
function statNumber(stats: unknown, path: readonly string[]): number | null {
  let node: unknown = stats;
  for (const key of path) {
    if (typeof node !== "object" || node === null) return null;
    node = (node as Record<string, unknown>)[key];
  }
  return typeof node === "number" ? node : null;
}

const CHANGE_ROWS = [
  { label: "Tamamlanan iş", path: ["todos", "completed"], unit: "" },
  { label: "Odak süresi", path: ["focus", "minutes"], unit: " dk" },
  { label: "Aktif gün", path: ["focus", "active_days"], unit: "" },
  { label: "Kart tekrarı", path: ["flashcards", "reviewed"], unit: "" },
] as const;

/**
 * Önceki kayda göre değişim satırları.
 *
 * Önceki kayıtta alan yoksa (eski kayıt biçimi) satır YAZILMAZ: eksik veriyi
 * sıfır sayıp "-12" demek ölçülmemiş bir iddia olurdu.
 */
export function reviewChangeRows(stats: ReviewPreview["stats"], previousStats: unknown): [string, string][] {
  const rows: [string, string][] = [];
  for (const row of CHANGE_ROWS) {
    const before = statNumber(previousStats, row.path);
    const now = statNumber(stats, row.path);
    if (before === null || now === null) continue;
    const delta = now - before;
    rows.push([row.label, delta === 0 ? "değişmedi" : `${delta > 0 ? "+" : ""}${delta}${row.unit}`]);
  }
  return rows;
}
