// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const harness = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), invalidate: vi.fn() }));
vi.mock("@/core/api", () => ({ api: harness }));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: harness.invalidate }));
import { InterviewIntelligencePanel } from "./InterviewIntelligencePanel";
import { CareerInsightsPanel } from "./CareerInsightsPanel";

function mount(node: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

it("shows unknown stage, stale evidence and disables stale practice", async () => {
  harness.get.mockResolvedValue({
    prep: {
      is_stale: true,
      role_summary: "Fixture role",
      interview_stage: null,
      focus_areas: ["Python"],
      likely_questions: [],
      questions_to_ask: [],
      story_recommendations: [],
      unknowns: ["missing_story_gap"],
    },
    practice: [],
  });
  mount(<InterviewIntelligencePanel interviewId="fixture" />);
  await screen.findByText("Kanıt değişti; yeniden hazırla");
  expect(screen.getByText(/Aşama bilinmiyor/)).toBeTruthy();
  fireEvent.click(screen.getByRole("tab", { name: "Prova" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Prova sorusu" }), { target: { value: "Question" } });
  fireEvent.change(screen.getByRole("textbox", { name: "Prova yanıtı" }), { target: { value: "Answer" } });
  expect((screen.getByRole("button", { name: "Kaydet" }) as HTMLButtonElement).disabled).toBe(true);
});

it("saves explicit user debrief without inferring outcome and invalidates centrally", async () => {
  harness.get.mockResolvedValue({ practice: [] });
  harness.post.mockResolvedValue({});
  mount(<InterviewIntelligencePanel interviewId="fixture" />);
  fireEvent.click(screen.getByRole("tab", { name: "Görüşme sonrası" }));
  fireEvent.change(screen.getByLabelText("Görüşmenin gerçekleşme zamanı"), { target: { value: "2026-09-20T12:00" } });
  fireEvent.change(screen.getByRole("textbox", { name: "Görüşme notları" }), {
    target: { value: "Difficulty with Python" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));
  await waitFor(() => expect(harness.post).toHaveBeenCalled());
  expect(harness.post.mock.calls[0][0]).toBe("/career/interviews/fixture/debrief");
  expect(harness.post.mock.calls[0][1].outcome_if_known).toBeNull();
  expect(harness.invalidate).toHaveBeenCalledWith("career.write");
});

it("shows error states without pretending a preparation succeeded", async () => {
  harness.get.mockRejectedValue(new Error("Fixture unavailable"));
  mount(<InterviewIntelligencePanel interviewId="fixture" />);
  await screen.findByRole("alert");
  expect(screen.queryByText("Güncel hazırlık")).toBeNull();
});

it("suppresses percentages for small samples and labels descriptive analytics", async () => {
  harness.get.mockResolvedValue({
    population: 1,
    minimum_sample: 3,
    funnel: { applied: 1 },
    conversions: { applied_to_interview: { numerator: 1, denominator: 1, rate: null, status: "insufficient_sample" } },
    skill_gaps: [],
    source_performance: [],
    geography: [],
    rejection_patterns: [],
    calibration: [],
    briefing: {},
    confidence_notes: ["Korelasyon neden değildir."],
  });
  mount(<CareerInsightsPanel />);
  await screen.findByText(/Yetersiz örnek/);
  expect(screen.queryByText("100.0%")).toBeNull();
  expect(screen.getByText("Korelasyon neden değildir.")).toBeTruthy();
});

it("shows the empty cohort without fabricating outcomes", async () => {
  harness.get.mockResolvedValue({
    population: 0,
    minimum_sample: 3,
    funnel: {},
    conversions: {},
    skill_gaps: [],
    source_performance: [],
    geography: [],
    rejection_patterns: [],
    calibration: [],
    briefing: {},
    confidence_notes: [],
  });
  mount(<CareerInsightsPanel />);
  await screen.findByText("Bu dönemde keşfedilmiş ilan yok");
});
