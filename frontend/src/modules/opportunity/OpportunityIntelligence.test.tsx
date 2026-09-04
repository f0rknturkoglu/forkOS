import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useQuery: vi.fn(({ queryKey }: { queryKey: string[] }) => ({
    data:
      queryKey[0] === "opportunity-silence"
        ? [
            {
              id: "opp-1",
              title: "Platform Engineer",
              organization: "Acme",
              status: "interview",
              last_interview_at: "2026-08-01T00:00:00Z",
              days_silent: 25,
            },
          ]
        : queryKey[0] === "followups" || queryKey[0] === "career-stories"
          ? []
          : { total: 0, by_status: [], conversions: {}, rejection_reasons: [] },
  })),
}));

vi.mock("@/core/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), del: vi.fn() },
}));

vi.mock("@/core/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/ui")>();
  return { ...actual, useToast: () => ({ push: vi.fn() }) };
});

import { ApplicationCrmPanel } from "./ApplicationCrmPanel";
import { ReplyProcessorSection, replySuggestionCanApply } from "./OpportunityDetailSections";
import { OpportunityEvaluationSection } from "./OpportunityEvaluationSection";

describe("career intelligence surfaces", () => {
  it("shows the reply processor as an explicit local action", () => {
    const html = renderToStaticMarkup(<ReplyProcessorSection id="opp-1" status="applied" online />);
    expect(html).toContain("Gelen yanıtı işle");
    expect(html).toContain("yalnızca bu cihazda analiz edilir");
    expect(html).toContain("Yanıt yapıştır");
  });

  it("shows applications that crossed the interview silence threshold", () => {
    const html = renderToStaticMarkup(<ApplicationCrmPanel />);
    expect(html).toContain("Firma sessizliği");
    expect(html).toContain("Platform Engineer");
    expect(html).toContain("25 gün");
  });

  it("offers a local two-pass evaluation before any result exists", () => {
    const html = renderToStaticMarkup(<OpportunityEvaluationSection id="opp-1" evaluation={null} online />);
    expect(html).toContain("İlanı iki aşamada değerlendir");
    expect(html).toContain("Hiçbir veri dışarı gönderilmez");
  });

  it("renders requirements, candidate matches and work authorization gate", () => {
    const html = renderToStaticMarkup(
      <OpportunityEvaluationSection
        id="opp-1"
        online
        evaluation={{
          version: "career-ops-v1",
          evaluated_at: "2026-09-04T12:00:00Z",
          source_fingerprint: "abc",
          engine: "local_rules",
          candidate_source: "document",
          candidate_document_id: "doc-1",
          candidate_document_title: "furkan-cv.pdf",
          archetype: "agentic",
          archetype_scores: { agentic: 4 },
          score: 25,
          recommendation: "skip",
          requirements: [
            {
              id: "req-k8s",
              name: "Kubernetes",
              importance: "high",
              evidence: "stated",
              excerpt: "Strong Kubernetes experience is required.",
              terms: ["Kubernetes"],
            },
          ],
          matches: [
            {
              requirement_id: "req-k8s",
              requirement: "Kubernetes",
              match: "partial",
              evidence: "Profilde Docker deneyimi var.",
              gap_mitigation: "İlişkili projeyi görünür kıl.",
              story_ids: [],
            },
          ],
          gate: {
            job_country: "Germany",
            authorized_to_work: false,
            sponsorship_status: "no_sponsorship",
            geo_mismatch: false,
            hard_blocker: true,
            reasons: ["Çalışma izni yok ve sponsorluk sunulmuyor."],
          },
          notes: null,
        }}
      />,
    );
    expect(html).toContain("Pass 1 · İlan gereksinimleri");
    expect(html).toContain("Pass 2 · Aday eşleşmesi");
    expect(html).toContain("Agentic Systems");
    expect(html).toContain("Hard blocker");
    expect(html).toContain("İlişkili projeyi görünür kıl");
    expect(html).toContain("furkan-cv.pdf");
  });

  it("does not offer invalid reply transitions from terminal states", () => {
    const rejection = {
      kind: "rejection" as const,
      label: "Red",
      confidence: 0.9,
      evidence: ["not moving forward"],
      suggested_status: "rejected" as const,
      suggested_todo_title: null,
      summary: "Başvuru reddedildi.",
    };
    expect(replySuggestionCanApply(rejection, "applied")).toBe(true);
    expect(replySuggestionCanApply(rejection, "rejected")).toBe(false);
    expect(replySuggestionCanApply(rejection, "accepted")).toBe(false);
  });
});
