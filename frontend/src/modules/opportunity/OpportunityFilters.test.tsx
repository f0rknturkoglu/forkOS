// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
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
  afterEach(cleanup);

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

  it("renders score range and both score sorts only for jobs", () => {
    const jobs = renderToStaticMarkup(<OpportunityFilters filters={filters} facets={{}} onChange={() => undefined} />);
    expect(jobs).toContain("Uyum skoru");
    expect(jobs).toContain("Minimum skor");
    expect(jobs).toContain("Maksimum skor");
    expect(jobs).toContain("70–100");
    expect(jobs).toContain("Skor: yüksekten düşüğe");
    expect(jobs).toContain("Skor: düşükten yükseğe");

    const announcements = renderToStaticMarkup(
      <OpportunityFilters
        filters={switchOpportunitySection(filters, "announcements")}
        facets={{}}
        onChange={() => undefined}
      />,
    );
    expect(announcements).not.toContain("Uyum skoru");
    expect(announcements).not.toContain("Minimum skor");
  });

  it("applies a score preset as an inclusive range", () => {
    const onChange = vi.fn();
    render(
      <OpportunityFilters
        filters={{ ...filters, min_score: undefined, max_score: undefined }}
        facets={{}}
        onChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "70–100" }));

    expect(onChange).toHaveBeenCalledWith({
      ...filters,
      min_score: 70,
      max_score: 100,
      offset: 0,
    });
  });
});
