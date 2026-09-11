/**
 * Fırsatlar URL sözleşmesi.
 *
 * Arama, görünüm, filtre ve seçili kayıt adres çubuğuna yazılır: tarayıcı
 * geri/ileri çalışır, yenilemede seçili kayıt yeniden açılır ve bir kayda
 * derin bağlantı (`?focus=<id>`) verilebilir. Entity rotası
 * (`/opportunities?focus={id}`) bu biçimle uyumludur.
 */

import type { OpportunityBrowseFilters, OpportunitySection } from "./opportunityBrowse";

export const OPPORTUNITY_TABS = ["jobs", "applications", "announcements", "career", "sources"] as const;
export type OpportunityTab = (typeof OPPORTUNITY_TABS)[number];

const SECTION_TABS: Record<OpportunitySection, OpportunityTab> = {
  jobs: "jobs",
  announcements: "announcements",
  trash: "jobs",
};

const TAB_SECTIONS: Partial<Record<OpportunityTab, OpportunitySection>> = {
  jobs: "jobs",
  announcements: "announcements",
};

export function tabForSection(section: OpportunitySection): OpportunityTab {
  return SECTION_TABS[section];
}

export function sectionForTab(tab: OpportunityTab, current: OpportunitySection): OpportunitySection {
  const section = TAB_SECTIONS[tab];
  if (section) return section;
  return current;
}

const FILTER_KEYS = [
  "search",
  "status",
  "source",
  "region",
  "remote",
  "archetype",
  "recommendation",
  "category",
  "skill",
  "announcement_source",
  "sort",
  "view",
] as const;

const NUMERIC_KEYS = ["period_days", "year", "min_score", "max_score", "min_skill_match", "max_skill_match"] as const;

interface OpportunityUrlState {
  tab: OpportunityTab;
  focus: string | null;
  story: string | null;
  connection: string | null;
  filters: OpportunityBrowseFilters;
  view: "rows" | "grid" | "kanban" | null;
}

export function serializeOpportunityUrl(state: OpportunityUrlState): string {
  const query = new URLSearchParams();
  query.set("tab", state.tab);
  if (state.filters.section !== "jobs") query.set("section", state.filters.section);
  if (state.focus) query.set("focus", state.focus);
  if (state.story) query.set("story", state.story);
  if (state.connection) query.set("connection", state.connection);
  for (const key of FILTER_KEYS) {
    const value = state.filters[key as keyof OpportunityBrowseFilters];
    if (value === undefined || value === "" || value === null) continue;
    query.set(key, String(value));
  }
  for (const key of NUMERIC_KEYS) {
    const value = state.filters[key as keyof OpportunityBrowseFilters];
    if (typeof value !== "number") continue;
    query.set(key, String(value));
  }
  if (state.filters.skill_match_state) query.set("skill_match_state", state.filters.skill_match_state);
  return query.toString();
}

export function parseOpportunityUrl(params: URLSearchParams, base: OpportunityBrowseFilters): OpportunityUrlState {
  const rawTab = params.get("tab");
  const tab = (OPPORTUNITY_TABS as readonly string[]).includes(rawTab ?? "") ? (rawTab as OpportunityTab) : "jobs";
  const filters: OpportunityBrowseFilters = { ...base, offset: 0 };
  const rawSection = params.get("section");
  if (rawSection === "jobs" || rawSection === "announcements" || rawSection === "trash") {
    filters.section = rawSection;
  } else if (tab === "jobs" || tab === "announcements") {
    filters.section = tab;
  }
  for (const key of FILTER_KEYS) {
    const value = params.get(key);
    if (value === null) continue;
    (filters as unknown as Record<string, unknown>)[key] = value;
  }
  for (const key of NUMERIC_KEYS) {
    const value = params.get(key);
    if (value === null || value === "") continue;
    const parsed = Number(value);
    if (Number.isFinite(parsed)) (filters as unknown as Record<string, unknown>)[key] = parsed;
  }
  const skillState = params.get("skill_match_state");
  if (skillState === "computed" || skillState === "uncomputed") {
    filters.skill_match_state = skillState;
  }
  const view = params.get("view");
  return {
    tab,
    focus: params.get("focus"),
    story: params.get("story"),
    connection: params.get("connection"),
    filters,
    view: view === "rows" || view === "grid" || view === "kanban" ? view : null,
  };
}
