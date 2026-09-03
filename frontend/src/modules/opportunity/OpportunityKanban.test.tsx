import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Opportunity } from "@/core/types";
import { OpportunityKanban } from "./OpportunityKanban";

describe("OpportunityKanban", () => {
  const dummyItem: Opportunity = {
    id: "opp-1",
    kind: "job",
    title: "Senior Backend Engineer",
    category: "software",
    organization: "TechCorp",
    url: "https://example.com/job",
    status: "interview",
    priority: 2,
    found_at: "2026-08-30T10:00:00Z",
    published_at: null,
    deadline_at: null,
    applied_at: null,
    location: "Remote",
    remote: "remote",
    compensation: null,
    source: "remoteok",
    external_id: null,
    raw: {},
    score: 85,
    score_reasons: null,
    notes: null,
    trashed_at: null,
    trashed_from_status: null,
    country: "TR",
    region: "EU",
    follow_up_at: null,
    rejection_reason: null,
    skill_match: {
      match_ratio: 0.8,
      matched: ["python", "docker"],
      missing: ["aws"],
    },
  };

  it("renders pipeline columns and places items into matching column", () => {
    const html = renderToStaticMarkup(<OpportunityKanban items={[dummyItem]} onOpen={vi.fn()} onStatus={vi.fn()} />);

    expect(html).toContain("Keşfedildi");
    expect(html).toContain("İnceleniyor");
    expect(html).toContain("Başvuruldu");
    expect(html).toContain("Mülakat");
    expect(html).toContain("Teklif");
    expect(html).toContain("Sonuçlandı");
    expect(html).toContain("Senior Backend Engineer");
    expect(html).toContain("TechCorp");
    expect(html).toContain("85p");
  });
});
