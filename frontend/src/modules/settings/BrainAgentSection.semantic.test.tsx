// @vitest-environment jsdom

/**
 * A4 — Hafıza adayları UI testleri.
 *
 * Epistemik etiketler, kullanıcı onay kapısı, terfi butonları ve yenileme.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as semanticApi from "@/core/agentSemantic";
import { SemanticCandidatesCard } from "./BrainAgentSection";

vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/ui", async () => {
  const actual = await vi.importActual<typeof import("@/core/ui")>("@/core/ui");
  return {
    ...actual,
    useToast: () => ({ push: vi.fn() }),
  };
});

vi.mock("@/core/agentSemantic", async () => {
  const actual = await vi.importActual<typeof semanticApi>("@/core/agentSemantic");
  return {
    ...actual,
    getAgentSemanticStatus: vi.fn(),
    listSemanticCandidates: vi.fn(),
    refreshSemanticCandidates: vi.fn(),
    confirmSemanticCandidate: vi.fn(),
    rejectSemanticCandidate: vi.fn(),
    promoteSemanticCandidate: vi.fn(),
  };
});

function wrap(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("Hafıza adayları kartı (A4)", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });
  beforeEach(() => {
    vi.mocked(semanticApi.getAgentSemanticStatus).mockResolvedValue({
      total_candidates: 2,
      needs_review_count: 1,
      ready_count: 1,
      proposed_count: 0,
      promoted_count: 0,
      rejected_count: 0,
      durable_card_count: 5,
    });
    vi.mocked(semanticApi.listSemanticCandidates).mockResolvedValue({
      items: [
        {
          id: "11111111-1111-1111-1111-111111111111",
          candidate_key: "cand_1",
          kind: "decision",
          statement: "SQLite yerine PostgreSQL kullanılacak.",
          scope: "global",
          scope_project: null,
          subject_key: null,
          domains: [],
          suggested_destination: "durable_vault",
          primary_evidence_class: "model_derived",
          evidence_refs: [{ ref: "turn:1" }],
          observed_at: "2026-09-23T12:00:00Z",
          valid_from: null,
          valid_to: null,
          rationale: null,
          conditions: [],
          exceptions: [],
          sensitivity: "normal",
          remote_allowed: false,
          status: "needs_review",
          reviewed_by: null,
          possible_related_card_ids: ["old_card_123"],
          warnings: [],
          recurrence_count: 1,
          first_seen_at: "2026-09-23T12:00:00Z",
          last_seen_at: "2026-09-23T12:00:00Z",
          revision: "rev_1",
          created_at: "2026-09-23T12:00:00Z",
          updated_at: "2026-09-23T12:00:00Z",
        },
        {
          id: "22222222-2222-2222-2222-222222222222",
          candidate_key: "cand_2",
          kind: "goal",
          statement: "Kullanıcı tercihi: make test ile doğrula.",
          scope: "project",
          scope_project: "forkOS",
          subject_key: null,
          domains: [],
          suggested_destination: "durable_vault",
          primary_evidence_class: "explicit_user",
          evidence_refs: [{ ref: "turn:2" }],
          observed_at: "2026-09-23T12:00:00Z",
          valid_from: null,
          valid_to: null,
          rationale: null,
          conditions: [],
          exceptions: [],
          sensitivity: "normal",
          remote_allowed: false,
          status: "ready",
          reviewed_by: "user",
          possible_related_card_ids: [],
          warnings: [],
          recurrence_count: 1,
          first_seen_at: "2026-09-23T12:00:00Z",
          last_seen_at: "2026-09-23T12:00:00Z",
          revision: "rev_2",
          created_at: "2026-09-23T12:00:00Z",
          updated_at: "2026-09-23T12:00:00Z",
        },
      ],
      total: 2,
    });
  });


  it("adayları ve kanıt etiketlerini Türkçe olarak gösterir", async () => {
    wrap(<SemanticCandidatesCard online={true} />);

    await waitFor(() => {
      expect(screen.queryByText(/SQLite yerine PostgreSQL kullanılacak/)).toBeTruthy();
      expect(screen.queryByText(/Kullanıcı tercihi: make test ile doğrula/)).toBeTruthy();
    });

    // Kanıt etiketleri
    expect(screen.queryByText("Agent çıkarımı")).toBeTruthy();
    expect(screen.queryByText("Kullanıcı açıkça söyledi")).toBeTruthy();

    // Benzer mevcut bilgi uyarısı
    expect(screen.queryByText(/Benzer mevcut bilgi: old_card_123/)).toBeTruthy();
  });

  it("Adayları tara eylemi refresh endpoint'ini çağırır", async () => {
    vi.mocked(semanticApi.refreshSemanticCandidates).mockResolvedValue({
      created_count: 1,
      updated_count: 0,
      total_candidates: 3,
    });

    wrap(<SemanticCandidatesCard online={true} />);

    const refreshBtn = await screen.findByText(/Adayları tara/);
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(semanticApi.refreshSemanticCandidates).toHaveBeenCalledTimes(1);
    });
  });

  it("Onayla butonu confirm API'sini çağırır", async () => {
    vi.mocked(semanticApi.confirmSemanticCandidate).mockResolvedValue({} as any);

    wrap(<SemanticCandidatesCard online={true} />);

    const confirmBtns = await screen.findAllByText(/Onayla/);
    expect(confirmBtns.length).toBeGreaterThan(0);
    fireEvent.click(confirmBtns[0]);

    await waitFor(() => {
      expect(semanticApi.confirmSemanticCandidate).toHaveBeenCalledWith(
        "11111111-1111-1111-1111-111111111111",
        "rev_1",
      );
    });
  });
});
