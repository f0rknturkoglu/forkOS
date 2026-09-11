/**
 * Kariyer çalışma alanının paylaşılan yerel yardımcıları.
 *
 * Buradaki hiçbir fonksiyon ağ çağrısı yapmaz; yalnızca backend'in kararlı
 * kurallarını arayüzde görünür kılar (kurum normalizasyonu, Connections.csv
 * önizlemesi, hikâye metni örtüşmesi).
 */
import type { CareerConnection, CareerStory, CareerStoryProvenance } from "@/core/types";

export const PROVENANCE_LABELS: Record<CareerStoryProvenance, string> = {
  existing: "Doğrudan yaşandı",
  supported: "Belgeyle destekli",
  "derived-unverified": "Türetilmiş · doğrulanmadı",
  "user-cannot-confirm": "Doğrulanamıyor",
};

/** Backend `career.COMPANY_STOP_WORDS` ile aynı küme. */
const COMPANY_STOP_WORDS: Record<string, true> = {
  a: true,
  as: true,
  co: true,
  company: true,
  corp: true,
  corporation: true,
  gmbh: true,
  group: true,
  inc: true,
  limited: true,
  llc: true,
  ltd: true,
  plc: true,
  sirketi: true,
  the: true,
};

/**
 * Kurum adını hukuki eklerden arındırıp kararlı token anahtarına çevirir.
 * Backend `career.normalize_company` ile birebir aynı kural: arayüzde gösterilen
 * normalizasyon ile eşleştirme aynı sonucu verir.
 */
export function normalizeCompany(value: string | null | undefined): string {
  if (!value) return "";
  const ascii = value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/&/g, " and ");
  const tokens = ascii.match(/[a-z0-9]+/g) ?? [];
  const unique = [...new Set(tokens.filter((token) => !COMPANY_STOP_WORDS[token]))];
  return unique.sort().join(" ");
}

/** Bir hikâyenin kaynak/etiket özeti; listede ve detayda aynı sırayla gösterilir. */
export function storySearchText(story: CareerStory): string {
  return [story.title, story.tags.join(" "), story.situation, story.task, story.action, story.result, story.reflection]
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase("tr");
}

/* ── Connections.csv önizlemesi (yazmadan önce) ───────────────────────── */

/** Ham LinkedIn satırı; başlık eşlemesinden sonra alan adları kanoniktir. */
interface ParsedConnectionRow {
  first_name: string;
  last_name: string;
  profile_url: string;
  email: string;
  company: string;
  position: string;
  connected_on: string;
}

interface ConnectionPreviewRow extends ParsedConnectionRow {
  /** Aynı kişiyi işaret eden kararlı yerel anahtar (hash değil, okunabilir). */
  identity: string;
  /** Bu satır ya dosya içinde ya da mevcut ağda zaten var. */
  duplicate: boolean;
}

export interface ConnectionPreview {
  total: number;
  duplicates: number;
  rows: ConnectionPreviewRow[];
}

/** RFC 4180'e yakın küçük ayrıştırıcı: tırnaklı alan + kaçırılmış tırnak. */
function splitCsvLine(line: string): string[] {
  const cells: string[] = [];
  let current = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (quoted) {
      if (char === '"') {
        if (line[index + 1] === '"') {
          current += '"';
          index += 1;
        } else {
          quoted = false;
        }
      } else {
        current += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      cells.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  cells.push(current.trim());
  return cells;
}

const HEADER_ALIASES: Record<keyof ParsedConnectionRow, string[]> = {
  first_name: ["first name", "ad"],
  last_name: ["last name", "soyad"],
  profile_url: ["url", "profile url", "linkedin url"],
  email: ["email address", "email", "e-posta"],
  company: ["company", "company name", "şirket", "sirket"],
  position: ["position", "title", "pozisyon"],
  connected_on: ["connected on", "connection date", "bağlantı tarihi"],
};

function matchHeader(cell: string): keyof ParsedConnectionRow | null {
  const normalized = cell.trim().toLocaleLowerCase("tr");
  for (const [field, aliases] of Object.entries(HEADER_ALIASES) as [keyof ParsedConnectionRow, string[]][]) {
    if (aliases.includes(normalized)) return field;
  }
  return null;
}

/** LinkedIn'in başa koyduğu açıklama satırlarını atlayıp veri satırlarını bulur. */
function parseConnectionsCsv(text: string): ParsedConnectionRow[] {
  const lines = text.split(/\r?\n/);
  let headerIndex = -1;
  let mapping: (keyof ParsedConnectionRow | null)[] = [];
  for (let index = 0; index < lines.length; index += 1) {
    const cells = splitCsvLine(lines[index]);
    const candidate = cells.map(matchHeader);
    if (candidate.includes("first_name") && candidate.includes("last_name")) {
      headerIndex = index;
      mapping = candidate;
      break;
    }
  }
  if (headerIndex === -1) return [];
  const rows: ParsedConnectionRow[] = [];
  for (const line of lines.slice(headerIndex + 1)) {
    if (!line.trim()) continue;
    const cells = splitCsvLine(line);
    const row: ParsedConnectionRow = {
      first_name: "",
      last_name: "",
      profile_url: "",
      email: "",
      company: "",
      position: "",
      connected_on: "",
    };
    mapping.forEach((field, cellIndex) => {
      if (field) row[field] = cells[cellIndex] ?? "";
    });
    if (row.first_name || row.last_name || row.profile_url || row.email) rows.push(row);
  }
  return rows;
}

/** Backend `_connection_identity` ile aynı öncelik: profil > e-posta > alanlar. */
function connectionIdentity(row: {
  first_name?: string | null;
  last_name?: string | null;
  profile_url?: string | null;
  email?: string | null;
  company?: string | null;
  position?: string | null;
}): string {
  const stable =
    row.profile_url?.trim() ||
    row.email?.trim() ||
    [row.first_name ?? "", row.last_name ?? "", normalizeCompany(row.company), row.position ?? ""].join("|");
  return stable.toLocaleLowerCase("tr");
}

/**
 * Dosya içi ve mevcut ağdaki tekrarları işaretler. Önizleme, yazma işleminden
 * ÖNCE çağrılır; hiçbir istek göndermez.
 */
export function previewConnectionsCsv(text: string, existing: CareerConnection[]): ConnectionPreview {
  const seen = new Set(existing.map((connection) => connectionIdentity(connection)));
  const rows = parseConnectionsCsv(text).map((row) => {
    const identity = connectionIdentity(row);
    const duplicate = seen.has(identity);
    seen.add(identity);
    return { ...row, identity, duplicate };
  });
  return { total: rows.length, duplicates: rows.filter((row) => row.duplicate).length, rows };
}

/* ── Hikâye metni örtüşmesi (ön yazı geri bağı) ───────────────────────── */

/** Backend `career.COMMON_WORDS` yerine kısa bir yerel durdurma listesi. */
const STORY_STOP_WORDS: Record<string, true> = {
  about: true,
  after: true,
  again: true,
  against: true,
  because: true,
  before: true,
  being: true,
  between: true,
  could: true,
  every: true,
  first: true,
  found: true,
  their: true,
  there: true,
  these: true,
  those: true,
  through: true,
  under: true,
  where: true,
  which: true,
  while: true,
  would: true,
};

function significantWords(value: string): Set<string> {
  const words = value.toLocaleLowerCase("tr").match(/[a-zà-ž0-9+#.]+/g) ?? [];
  return new Set(words.filter((word) => word.length >= 5 && !STORY_STOP_WORDS[word]));
}

/** Bir ön yazının hikâye metniyle örtüşüp örtüşmediği (yerel tarama). */
export function storyOverlapsText(story: CareerStory, text: string): boolean {
  const textWords = significantWords(text);
  if (textWords.size === 0) return false;
  const tagWords = significantWords(story.tags.join(" "));
  if ([...tagWords].some((word) => textWords.has(word))) return true;
  const evidence = significantWords(
    [story.title, story.situation, story.task, story.action, story.result, story.reflection].filter(Boolean).join(" "),
  );
  return [...evidence].filter((word) => textWords.has(word)).length >= 2;
}
