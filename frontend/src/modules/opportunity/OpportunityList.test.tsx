import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Opportunity } from "@/core/types";
import { FilterChip, OpportunityCard, OpportunityCollection } from "./OpportunityList";

const item = {
  id: "1",
  title: "Frontend Developer",
  kind: "job",
  category: "software",
  organization: "forkOS",
  url: "https://example.com/job",
  status: "discovered",
  priority: 2,
  found_at: "2026-08-23T10:00:00Z",
  published_at: "2026-08-22T10:00:00Z",
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
    expect(html).toContain("Yazılım &amp; mühendislik");
    expect(html).toContain("Çöpe at");
  });

  it("uses a real responsive collection in grid mode", () => {
    const html = renderToStaticMarkup(
      <OpportunityCollection layout="grid"><span>card</span></OpportunityCollection>,
    );
    expect(html).toContain("grid-cols-1");
    expect(html).toContain("md:grid-cols-2");
    expect(html).toContain("xl:grid-cols-3");
  });

  it("renders announcements without a score", () => {
    const html = renderToStaticMarkup(
      <OpportunityCard
        item={{ ...item, kind: "exam", category: null, score: null, published_at: "2026-08-26T00:00:00Z" }}
        disabled={false}
        isTrash={false}
        onOpen={() => undefined}
        onStatus={() => undefined}
        onTrash={() => undefined}
        onRestore={() => undefined}
        onDelete={() => undefined}
      />,
    );
    expect(html).toContain("26 Ağu 2026");
    expect(html).not.toContain("skor");
  });

  it("renders filter count and selected state", () => {
    const html = renderToStaticMarkup(<FilterChip label="İş İlanları" count={12} active onClick={() => undefined} />);
    expect(html).toContain('aria-pressed="true"');
    expect(html).toContain("12");
  });
});
