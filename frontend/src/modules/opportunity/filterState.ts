/**
 * Fırsat filtrelerinin TEK kayıt defteri.
 *
 * Önceden aynı filtre kümesi beş ayrı yerde elle sayılıyordu (aktif sayısı,
 * chip listesi, "tümünü temizle", kayıtlı görünüm whitelist'i, bölüm geçişi);
 * bir filtre eklemek beş dosyaya dokunmayı gerektiriyordu ve biri unutulunca
 * "Aktif Filtreler" kutusu boş görünüyordu (YLSY chip'i bu yüzden yoktu).
 * Artık tanım burada; UI bu tanımdan üretilir.
 */

import { sourceLabel } from "@/core/labels";
import type { OpportunityBrowseFilters, OpportunitySection } from "./opportunityBrowse";
import { REMOTE_LABELS, archetypeLabel, recommendationLabel, statusLabel, type RemoteKind } from "./labels";

type FilterKey = keyof OpportunityBrowseFilters;

interface ActiveFilterChip {
  key: FilterKey;
  /** Kullanıcıya görünen chip metni. */
  label: string;
  /** Yalnızca bu filtreyi temizler. */
  clear: (filters: OpportunityBrowseFilters) => OpportunityBrowseFilters;
}

interface FilterDescriptor {
  key: FilterKey;
  /** Hangi bölümlerde geçerli olduğu. */
  sections: readonly OpportunitySection[];
  /** Kayıtlı görünüme yazılıp yazılmayacağı. */
  saved?: boolean;
  /** Aktifken chip metni; pasifken undefined. */
  label?: (filters: OpportunityBrowseFilters) => string | undefined;
}

const ALL: readonly OpportunitySection[] = ["jobs", "announcements", "trash"];
const JOBS: readonly OpportunitySection[] = ["jobs"];
const RESULTS: readonly OpportunitySection[] = ["jobs", "announcements"];

export const SCORE_PRESETS = [
  { label: "Tümü", min: undefined, max: undefined },
  { label: "80–100", min: 80, max: 100 },
  { label: "70–79", min: 70, max: 79.99 },
  { label: "40–69", min: 40, max: 69.99 },
  { label: "0–39", min: 0, max: 39.99 },
  { label: "Elendi", min: -1, max: -1 },
] as const;

/** Hazır uyum presetleri. Aralıklar ÖRTÜŞMEZ; eşikler tek yerden gelir. */
export const PROFILE_MATCH_PRESETS = [
  { label: "Tümü", tier: undefined, min: undefined, max: undefined, state: undefined },
  { label: "%70+", tier: "high", min: 0.7, max: undefined, state: undefined },
  { label: "%40–69", tier: "mid", min: 0.4, max: 0.6999, state: undefined },
  { label: "%1–39", tier: "low", min: 0.01, max: 0.3999, state: undefined },
  { label: "%0", tier: "zero", min: 0, max: 0, state: undefined },
  {
    label: "Hesaplanmadı",
    tier: "uncomputed",
    min: undefined,
    max: undefined,
    state: "uncomputed" as const,
  },
] as const;

const FILTER_DESCRIPTORS: readonly FilterDescriptor[] = [
  {
    key: "search",
    sections: ALL,
    saved: true,
    label: (f) => (f.search?.trim() ? `Arama: ${f.search.trim()}` : undefined),
  },
  {
    key: "source",
    sections: ALL,
    saved: true,
    label: (f) => (f.source ? `Kaynak: ${sourceLabel(f.source)}` : undefined),
  },
  {
    key: "status",
    sections: ALL,
    saved: true,
    label: (f) => (f.status ? `Durum: ${statusLabel(f.status)}` : undefined),
  },
  {
    key: "source_status",
    sections: RESULTS,
    saved: true,
    label: (f) => {
      if (f.source_status === "stale") return "Kaynakta bulunamıyor";
      if (f.source_status === "all") return "Tüm kaynak durumları";
      return undefined;
    },
  },
  {
    key: "category",
    sections: JOBS,
    saved: true,
    label: (f) => (f.category ? `Kategori: ${f.category}` : undefined),
  },
  {
    key: "region",
    sections: JOBS,
    saved: true,
    label: (f) =>
      f.region ? `Konum: ${f.region === "TR" ? "Türkiye" : f.region === "EU" ? "Avrupa" : f.region}` : undefined,
  },
  {
    key: "remote",
    sections: JOBS,
    saved: true,
    label: (f) => (f.remote ? `Çalışma: ${REMOTE_LABELS[f.remote as RemoteKind] ?? f.remote}` : undefined),
  },
  {
    key: "archetype",
    sections: JOBS,
    saved: true,
    label: (f) => (f.archetype ? `Rol: ${archetypeLabel(f.archetype)}` : undefined),
  },
  {
    key: "recommendation",
    sections: JOBS,
    saved: true,
    label: (f) => (f.recommendation ? `Karar: ${recommendationLabel(f.recommendation)}` : undefined),
  },
  {
    key: "skill",
    sections: JOBS,
    saved: true,
    label: (f) => (f.skill?.trim() ? `Beceri: ${f.skill.trim()}` : undefined),
  },
  {
    key: "announcement_source",
    sections: ["announcements"],
    saved: true,
    label: (f) => {
      if (!f.announcement_source) return undefined;
      const labels: Record<string, string> = { ylsy: "YLSY", osym: "ÖSYM", other: "Diğer" };
      return `Duyuru: ${labels[f.announcement_source] ?? f.announcement_source}`;
    },
  },
  {
    key: "period_days",
    sections: ["announcements"],
    saved: true,
    label: (f) => (f.period_days ? (f.period_days === 365 ? "Son 1 yıl" : `Son ${f.period_days} gün`) : undefined),
  },
  {
    key: "year",
    sections: ["announcements"],
    saved: true,
    label: (f) => (f.year ? `Yıl: ${f.year}` : undefined),
  },
];

/** Skor ve uyum chip'leri tek anahtar değil, ikili alan taşıdığı için ayrı. */

function scoreChip(filters: OpportunityBrowseFilters): ActiveFilterChip | null {
  if (filters.min_score === undefined && filters.max_score === undefined) return null;
  const preset = SCORE_PRESETS.find((item) => item.min === filters.min_score && item.max === filters.max_score);
  return {
    key: "min_score",
    label: `Skor: ${preset ? preset.label : scoreRangeLabel(filters.min_score, filters.max_score)}`,
    clear: (current) => ({ ...current, min_score: undefined, max_score: undefined, offset: 0 }),
  };
}

function profileMatchChip(filters: OpportunityBrowseFilters): ActiveFilterChip | null {
  const active =
    filters.min_skill_match !== undefined ||
    filters.max_skill_match !== undefined ||
    Boolean(filters.skill_match_state);
  if (!active) return null;
  const preset = PROFILE_MATCH_PRESETS.find(
    (item) =>
      item.min === filters.min_skill_match &&
      item.max === filters.max_skill_match &&
      (item.state ?? undefined) === (filters.skill_match_state ?? undefined),
  );
  const label = preset
    ? `Profil uyumu: ${preset.label}`
    : filters.skill_match_state === "uncomputed"
      ? "Profil uyumu: hesaplanmadı"
      : `Profil uyumu: %${Math.round((filters.min_skill_match ?? 0) * 100)}+`;
  return {
    key: "min_skill_match",
    label,
    clear: (current) => ({
      ...current,
      min_skill_match: undefined,
      max_skill_match: undefined,
      skill_match_state: undefined,
      skill_tier: undefined,
      offset: 0,
    }),
  };
}

/** Metinsel skor aralığı: "-1" kullanıcıya "Elendi" olarak görünür. */
export function scoreRangeLabel(min: number | undefined, max: number | undefined): string {
  if (min === undefined && max === undefined) return "Tüm skorlar";
  if (min === -1 && max === -1) return "Elendi";
  const low = min === undefined ? 0 : min === -1 ? "Elendi" : min;
  const high = max === undefined ? 100 : max === -1 ? "Elendi" : max;
  return `${low}–${high}`;
}

/** Geçerli bölümde aktif olan filtrelerin chip listesi (hepsi görünür). */
export function activeFilterChips(filters: OpportunityBrowseFilters): ActiveFilterChip[] {
  const chips: ActiveFilterChip[] = [];
  for (const descriptor of FILTER_DESCRIPTORS) {
    if (!descriptor.sections.includes(filters.section)) continue;
    const text = descriptor.label?.(filters);
    if (!text) continue;
    chips.push({
      key: descriptor.key,
      label: text,
      clear: (current) => ({ ...current, [descriptor.key]: undefined, offset: 0 }),
    });
  }
  const score = scoreChip(filters);
  if (score && filters.section === "jobs") chips.push(score);
  const profile = profileMatchChip(filters);
  if (profile && filters.section === "jobs") chips.push(profile);
  if (filters.skill_tier && !profile) {
    chips.push({
      key: "skill_tier",
      label: `Profil uyumu: ${filters.skill_tier}`,
      clear: (current) => ({ ...current, skill_tier: undefined, offset: 0 }),
    });
  }
  return chips;
}

/** Görünümde tutulan ama chip'i olmayan alanlar (sıralama, limit). */
const VIEW_KEYS: FilterKey[] = ["sort"];

/** Kayıtlı görünüme yazılan anahtarlar. */
export function savableView(filters: OpportunityBrowseFilters): Record<string, unknown> {
  const out: Record<string, unknown> = { section: filters.section };
  const keys = new Set<FilterKey>([
    ...FILTER_DESCRIPTORS.filter((item) => item.saved).map((item) => item.key),
    ...VIEW_KEYS,
    "min_score",
    "max_score",
    "min_skill_match",
    "max_skill_match",
    "skill_match_state",
    "skill_tier",
  ]);
  for (const key of keys) {
    const value = filters[key];
    if (value === undefined || value === "") continue;
    out[key] = value;
  }
  return out;
}

/** Kayıtlı görünümden bilinen anahtarları uygular; bilinmeyenleri yok sayar. */
export function applySavedView(filters: OpportunityBrowseFilters, raw: unknown): OpportunityBrowseFilters {
  const data = (raw ?? {}) as Record<string, unknown>;
  const section = data.section;
  const targetSection =
    section === "jobs" || section === "announcements" || section === "trash" ? section : filters.section;
  const base = targetSection === filters.section ? filters : switchSection(filters, targetSection);
  const draft = { ...base, offset: 0 } as unknown as Record<string, unknown>;
  for (const descriptor of FILTER_DESCRIPTORS) {
    const value = data[descriptor.key];
    if (typeof value === "string" || typeof value === "number") {
      draft[descriptor.key] = value;
    }
  }
  for (const key of ["min_score", "max_score", "min_skill_match", "max_skill_match"] as const) {
    const value = data[key];
    if (typeof value === "number") draft[key] = value;
  }
  if (data.skill_match_state === "computed" || data.skill_match_state === "uncomputed") {
    draft.skill_match_state = data.skill_match_state;
  }
  if (typeof data.skill_tier === "string") draft.skill_tier = data.skill_tier;
  if (typeof data.sort === "string") draft.sort = data.sort;
  return draft as unknown as OpportunityBrowseFilters;
}

/**
 * Bölüm geçişi: yalnızca hedef bölümde geçersiz filtreler temizlenir,
 * ortak filtreler (arama, kaynak, durum) korunur.
 */
export function switchSection(
  filters: OpportunityBrowseFilters,
  section: OpportunitySection,
): OpportunityBrowseFilters {
  const draft = { ...filters, section, offset: 0 } as unknown as Record<string, unknown>;
  const keep = new Set<string>();
  for (const descriptor of FILTER_DESCRIPTORS) {
    if (descriptor.sections.includes(section)) keep.add(descriptor.key);
  }
  for (const descriptor of FILTER_DESCRIPTORS) {
    if (!keep.has(descriptor.key)) draft[descriptor.key] = undefined;
  }
  if (section !== "jobs") {
    draft.min_score = undefined;
    draft.max_score = undefined;
    draft.min_skill_match = undefined;
    draft.max_skill_match = undefined;
    draft.skill_match_state = undefined;
    draft.skill_tier = undefined;
  }
  draft.sort = section === "jobs" ? "score" : "newest";
  return draft as unknown as OpportunityBrowseFilters;
}

export function clearAllFilters(filters: OpportunityBrowseFilters): OpportunityBrowseFilters {
  const draft = { ...filters, offset: 0 } as unknown as Record<string, unknown>;
  for (const descriptor of FILTER_DESCRIPTORS) {
    draft[descriptor.key] = undefined;
  }
  draft.min_score = undefined;
  draft.max_score = undefined;
  draft.min_skill_match = undefined;
  draft.max_skill_match = undefined;
  draft.skill_match_state = undefined;
  draft.skill_tier = undefined;
  return draft as unknown as OpportunityBrowseFilters;
}
