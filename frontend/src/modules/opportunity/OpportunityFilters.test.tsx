import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { OpportunityFilters } from "./OpportunityFilters";
import { browseQuery, switchOpportunitySection, type OpportunityBrowseFilters } from "./opportunityBrowse";

const filters: OpportunityBrowseFilters = {
  section: "jobs",
  category: "software",
  region: "EU",
  remote: "remote",
  search: "react",
  min_score: 40,
  max_score: 80,
  sort: "score",
  offset: 0,
  limit: 60,
};

describe("opportunity contextual filters", () => {
  it("only sends filters that belong to the active workspace", () => {
    expect(browseQuery(filters)).toContain("category=software");
    expect(browseQuery(filters)).toContain("min_score=40");
    expect(browseQuery(filters)).toContain("max_score=80");
    const announcements = switchOpportunitySection(filters, "announcements");
    const query = browseQuery({ ...announcements, announcement_source: "ylsy", year: 2026 });
    expect(query).toContain("announcement_source=ylsy");
    expect(query).toContain("year=2026");
    expect(query).not.toContain("category=");
    expect(query).not.toContain("remote=");
    expect(query).not.toContain("min_score=");
    expect(query).not.toContain("max_score=");
    expect(announcements.min_score).toBeUndefined();
    expect(announcements.max_score).toBeUndefined();
    expect(announcements.search).toBe("react");
    expect(announcements.sort).toBe("newest");
  });

  it("renders job categories only in jobs", () => {
    const jobs = renderToStaticMarkup(
      <OpportunityFilters filters={filters} facets={{ categories: { software: 12 } }} onChange={() => undefined} />,
    );
    expect(jobs).toContain("Yazılım &amp; mühendislik");
    const announcements = renderToStaticMarkup(
      <OpportunityFilters
        filters={switchOpportunitySection(filters, "announcements")}
        facets={{ announcement_sources: { ylsy: 4, osym: 7 } }}
        onChange={() => undefined}
      />,
    );
    expect(announcements).toContain("YLSY");
    expect(announcements).not.toContain("Yazılım &amp; mühendislik");
  });
});
