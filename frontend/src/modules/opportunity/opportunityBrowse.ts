import { qs } from "@/core/api";
import type { Opportunity } from "@/core/types";

export type OpportunitySection = "jobs" | "announcements" | "trash";
type AnnouncementSource = "ylsy" | "osym" | "other";
type OpportunitySort = "score" | "score_asc" | "skill_match" | "newest" | "oldest" | "deadline";

export interface OpportunityBrowseFilters {
  section: OpportunitySection;
  announcement_source?: AnnouncementSource | "";
  category?: string;
  search?: string;
  status?: string;
  source?: string;
  region?: string;
  remote?: string;
  archetype?: string;
  recommendation?: string;
  period_days?: number;
  year?: number;
  min_score?: number;
  max_score?: number;
  /** Kalite skoru hesaplanmış mı? `null` skoru ayri secmek icin. */
  score_state?: "computed" | "uncomputed" | "";
  skill?: string;
  min_skill_match?: number;
  max_skill_match?: number;
  /** null (hesaplanmadı) durumunu ayrı seçebilmek için. */
  skill_match_state?: "computed" | "uncomputed" | "";
  skill_tier?: string;
  /**
   * Kaynak durumu görünümü. `active` (varsayılan): kaynakta hâlâ görünen
   * ilanlar. `stale`: kaynakta kaybolmuş ("Kaynakta bulunamıyor") kayıtlar.
   * `all`: ikisi birlikte.
   */
  source_status?: "active" | "stale" | "all";
  sort: OpportunitySort;
  offset: number;
  limit: number;
}

export interface OpportunityBrowseResponse {
  items: Opportunity[];
  total: number;
  offset: number;
  limit: number;
  section_counts: Record<OpportunitySection, number>;
  facets: Record<string, Record<string, number>>;
}

export function browseQuery(filters: OpportunityBrowseFilters): string {
  const jobs = filters.section === "jobs";
  const announcements = filters.section === "announcements";
  return `/opportunities/browse${qs({
    section: filters.section,
    announcement_source: announcements ? filters.announcement_source : undefined,
    category: jobs ? filters.category : undefined,
    search: filters.search,
    status: filters.status,
    source: filters.source,
    region: jobs ? filters.region : undefined,
    remote: jobs ? filters.remote : undefined,
    archetype: jobs ? filters.archetype : undefined,
    recommendation: jobs ? filters.recommendation : undefined,
    period_days: announcements ? filters.period_days : undefined,
    year: announcements ? filters.year : undefined,
    min_score: jobs ? filters.min_score : undefined,
    max_score: jobs ? filters.max_score : undefined,
    score_state: jobs ? filters.score_state : undefined,
    skill: jobs ? filters.skill : undefined,
    min_skill_match: jobs ? filters.min_skill_match : undefined,
    max_skill_match: jobs ? filters.max_skill_match : undefined,
    skill_match_state: jobs ? filters.skill_match_state : undefined,
    // Kaynak durumu görünümü çöp dışındaki her bölümde geçerlidir: "Kaynakta
    // bulunamıyor" listesi iş ilanları kadar duyurular için de anlamlıdır.
    source_status: filters.section === "trash" ? undefined : (filters.source_status ?? "active"),
    sort: filters.sort,
    offset: filters.offset,
    limit: filters.limit,
  })}`;
}
