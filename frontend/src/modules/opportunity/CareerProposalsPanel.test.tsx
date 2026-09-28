// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type * as UiModule from "@/core/ui";
import type { components } from "@/generated/api-schema";

const apiMock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/core/api", () => ({ api: apiMock }));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/core/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof UiModule>();
  return { ...actual, useToast: () => ({ push: vi.fn() }) };
});

import { CareerProposalsPanel } from "./CareerProposalsPanel";

type Proposal = components["schemas"]["ProposalOut"];
const proposal = {
  id: "00000000-0000-4000-8000-000000000001",
  created_at: "2026-09-28T00:00:00Z",
  decided_at: null,
  fingerprint: "f1",
  related_goal_id: null,
  strategy_revision: "r1",
  target_id: null,
  target_type: null,
  type: "goal",
  title: "Ölçülebilir hedef",
  rationale: "Onaylı semantik yön",
  evidence_refs: ["memory:g1"],
  sample_size: 1,
  estimated_scope: "Tek hedef",
  status: "proposed",
  materialization_status: "pending",
  warnings: [],
} satisfies Proposal;

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <CareerProposalsPanel />
    </QueryClientProvider>,
  );
}

describe("CareerProposalsPanel", () => {
  beforeEach(() => {
    apiMock.get.mockResolvedValue([proposal]);
    apiMock.post.mockResolvedValue({ ...proposal, status: "materialized", materialization_status: "materialized" });
  });
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("yalnız açık onay tıklamasıyla materialization ucunu çağırır", async () => {
    mount();
    await screen.findByText("Ölçülebilir hedef");
    expect(apiMock.post).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Onayla ve oluştur" }));
    await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith(`/career/strategy/proposals/${proposal.id}/approve`));
  });

  it("ret kararı canonical oluşturma ucunu çağırmaz", async () => {
    mount();
    await screen.findByText("Ölçülebilir hedef");
    fireEvent.click(screen.getByRole("button", { name: "Reddet" }));
    await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith(`/career/strategy/proposals/${proposal.id}/reject`));
  });
});
