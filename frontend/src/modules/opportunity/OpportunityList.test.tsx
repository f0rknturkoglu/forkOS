import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Opportunity } from "@/core/types";
import { FilterChip, OpportunityCard } from "./OpportunityList";

const item = {
  id: "1",
  title: "Frontend Developer",
  kind: "job",
  organization: "forkOS",
  url: "https://example.com/job",
  status: "discovered",
  priority: 2,
  found_at: "2026-08-23T10:00:00Z",
  deadline_at: null,
  applied_at: null,
  location: "İstanbul",
  remote: "remote",
  compensation: null,
  source: "test",
  external_id: null,
  raw: {},
  score: 82,
  score_reasons: null,
  notes: null,
  trashed_at: null,
  trashed_from_status: null,
  country: null,
  region: null,
  follow_up_at: null,
  rejection_reason: null,
} satisfies Opportunity;

describe("opportunity list components", () => {
  it("renders score and actions without page state", () => {
    const html = renderToStaticMarkup(
      <OpportunityCard
        item={item}
        disabled={false}
        isTrash={false}
        onOpen={() => undefined}
        onStatus={() => undefined}
        onTrash={() => undefined}
        onRestore={() => undefined}
        onDelete={() => undefined}
      />,
    );

    expect(html).toContain("82");
    expect(html).toContain("Frontend Developer");
    expect(html).toContain("Çöpe at");
  });

  it("renders filter count and selected state", () => {
    const html = renderToStaticMarkup(<FilterChip label="İş İlanları" count={12} active onClick={() => undefined} />);
    expect(html).toContain('aria-pressed="true"');
    expect(html).toContain("12");
  });
});
