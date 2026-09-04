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
  skill?: string;
  min_skill_match?: number;
  skill_tier?: string;
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
    skill: jobs ? filters.skill : undefined,
    min_skill_match: jobs ? filters.min_skill_match : undefined,
    sort: filters.sort,
    offset: filters.offset,
    limit: filters.limit,
  })}`;
}

export function switchOpportunitySection(
  filters: OpportunityBrowseFilters,
  section: OpportunitySection,
): OpportunityBrowseFilters {
  const common = { ...filters, section, offset: 0 };
  if (section === "jobs") {
    return {
      ...common,
      announcement_source: "",
      period_days: undefined,
      year: undefined,
      sort: "score",
    };
  }
  return {
    ...common,
    category: "",
    region: "",
    remote: "",
    archetype: undefined,
    recommendation: undefined,
    min_score: undefined,
    max_score: undefined,
    skill: undefined,
    min_skill_match: undefined,
    skill_tier: undefined,
    announcement_source: section === "announcements" ? common.announcement_source : "",
    period_days: section === "announcements" ? common.period_days : undefined,
    year: section === "announcements" ? common.year : undefined,
    sort: "newest",
  };
}
