import { describe, expect, it } from "vitest";
import type { OpportunityBrowseFilters } from "./opportunityBrowse";
import { parseOpportunityUrl, serializeOpportunityUrl } from "./opportunityUrl";

const base: OpportunityBrowseFilters = { section: "jobs", sort: "score", offset: 0, limit: 60 };

describe("opportunity url contract", () => {
  it("round-trips the workspace, selection and filters", () => {
    const filters: OpportunityBrowseFilters = {
      ...base,
      search: "react",
      section: "announcements",
      announcement_source: "ylsy",
      year: 2026,
      period_days: 90,
      sort: "newest",
    };
    const query = serializeOpportunityUrl({
      tab: "announcements",
      focus: "abc-123",
      story: null,
      connection: null,
      filters,
      view: null,
    });
    const parsed = parseOpportunityUrl(new URLSearchParams(query), base);
    expect(parsed.tab).toBe("announcements");
    expect(parsed.focus).toBe("abc-123");
    expect(parsed.filters.search).toBe("react");
    expect(parsed.filters.announcement_source).toBe("ylsy");
    expect(parsed.filters.year).toBe(2026);
    expect(parsed.filters.period_days).toBe(90);
    expect(parsed.filters.section).toBe("announcements");
  });

  it("deep-links a job from the registry route (/opportunities?focus=<id>)", () => {
    const parsed = parseOpportunityUrl(new URLSearchParams("focus=opp-9"), base);
    expect(parsed.focus).toBe("opp-9");
    expect(parsed.tab).toBe("jobs");
    expect(parsed.filters.section).toBe("jobs");
  });

  it("keeps an explicit trash section across a reload", () => {
    const query = serializeOpportunityUrl({
      tab: "jobs",
      focus: null,
      story: null,
      connection: null,
      filters: { ...base, section: "trash" },
      view: null,
    });
    const parsed = parseOpportunityUrl(new URLSearchParams(query), base);
    expect(parsed.filters.section).toBe("trash");
  });

  it("restores the non-browse workspaces and their focus params", () => {
    const parsed = parseOpportunityUrl(new URLSearchParams("tab=career&story=s-1&connection=c-2"), base);
    expect(parsed.tab).toBe("career");
    expect(parsed.story).toBe("s-1");
    expect(parsed.connection).toBe("c-2");
  });

  it("carries the score and profile-match bounds as numbers", () => {
    const query = serializeOpportunityUrl({
      tab: "jobs",
      focus: null,
      story: null,
      connection: null,
      filters: { ...base, min_score: -1, max_score: 100, max_skill_match: 0.6999 },
      view: "grid",
    });
    const parsed = parseOpportunityUrl(new URLSearchParams(query), base);
    expect(parsed.filters.min_score).toBe(-1);
    expect(parsed.filters.max_score).toBe(100);
    expect(parsed.filters.max_skill_match).toBe(0.6999);
  });

  it("ignores an unknown tab instead of breaking the page", () => {
    const parsed = parseOpportunityUrl(new URLSearchParams("tab=nope"), base);
    expect(parsed.tab).toBe("jobs");
  });
});

describe("opportunity url round-trip", () => {
  const cases = [
    {
      name: "kariyer hikâyesi entity rotası doğrudan Kariyer sekmesini açar",
      url: "story=story-1",
      tab: "career" as const,
      story: "story-1",
    },
    {
      name: "kariyer bağlantısı entity rotası doğrudan Kariyer sekmesini açar",
      url: "connection=conn-1",
      tab: "career" as const,
      connection: "conn-1",
    },
    {
      name: "ilan derin bağlantısı İşler sekmesini korur",
      url: "focus=opp-1",
      tab: "jobs" as const,
      focus: "opp-1",
    },
  ];

  for (const item of cases) {
    it(item.name, () => {
      const parsed = parseOpportunityUrl(new URLSearchParams(item.url), base);
      expect(parsed.tab).toBe(item.tab);
      if ("story" in item) expect(parsed.story).toBe(item.story);
      if ("connection" in item) expect(parsed.connection).toBe(item.connection);
      if ("focus" in item) expect(parsed.focus).toBe(item.focus);
    });
  }

  it("serialize → parse → serialize aynı adresi üretir", () => {
    const state = {
      tab: "jobs" as const,
      focus: "opp-42",
      story: null,
      connection: null,
      filters: {
        ...base,
        search: "react",
        source_status: "stale" as const,
        skill_match_state: "computed" as const,
        skill_tier: "high",
        min_score: 70,
        max_score: 79.99,
        remote: "hybrid",
      },
      view: "grid" as const,
    };

    const first = serializeOpportunityUrl(state);
    const parsed = parseOpportunityUrl(new URLSearchParams(first), base);
    const second = serializeOpportunityUrl({
      tab: parsed.tab,
      focus: parsed.focus,
      story: parsed.story,
      connection: parsed.connection,
      filters: parsed.filters,
      view: parsed.view,
    });

    expect(second).toBe(first);
    expect(parsed.view).toBe("grid");
    expect(parsed.filters.source_status).toBe("stale");
    expect(parsed.filters.skill_tier).toBe("high");
    expect(parsed.filters.min_score).toBe(70);
  });

  it("görünüm parametresi adres çubuğunda korunur", () => {
    const query = serializeOpportunityUrl({
      tab: "jobs",
      focus: null,
      story: null,
      connection: null,
      filters: base,
      view: "kanban",
    });

    expect(new URLSearchParams(query).get("view")).toBe("kanban");
    expect(parseOpportunityUrl(new URLSearchParams(query), base).view).toBe("kanban");
  });
});
