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

const TAB_SECTIONS: Partial<Record<OpportunityTab, OpportunitySection>> = {
  jobs: "jobs",
  announcements: "announcements",
};

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
  "source_status",
  "sort",
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
  if (state.view) query.set("view", state.view);
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
  if (state.filters.score_state) query.set("score_state", state.filters.score_state);
  if (state.filters.skill_tier) query.set("skill_tier", state.filters.skill_tier);
  return query.toString();
}

export function parseOpportunityUrl(params: URLSearchParams, base: OpportunityBrowseFilters): OpportunityUrlState {
  const rawTab = params.get("tab");
  const story = params.get("story");
  const connection = params.get("connection");
  const explicitTab = (OPPORTUNITY_TABS as readonly string[]).includes(rawTab ?? "")
    ? (rawTab as OpportunityTab)
    : null;
  // Kariyer kayitlarinin entity rotasi (`?story=` / `?connection=`) sekme
  // tasimaz; hedef sekme buradan turetilir, aksi halde graf ve entity
  // deep-link'leri "Isler" sekmesini acardi.
  const derivedTab: OpportunityTab = story || connection ? "career" : "jobs";
  const tab = explicitTab ?? derivedTab;
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
  const scoreState = params.get("score_state");
  if (scoreState === "computed" || scoreState === "uncomputed") {
    filters.score_state = scoreState;
  }
  const skillState = params.get("skill_match_state");
  if (skillState === "computed" || skillState === "uncomputed") {
    filters.skill_match_state = skillState;
  }
  const skillTier = params.get("skill_tier");
  if (skillTier) filters.skill_tier = skillTier;
  const view = params.get("view");
  return {
    tab,
    focus: params.get("focus"),
    story,
    connection,
    filters,
    view: view === "rows" || view === "grid" || view === "kanban" ? view : null,
  };
}
