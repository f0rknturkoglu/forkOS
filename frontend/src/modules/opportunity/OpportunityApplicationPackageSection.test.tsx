// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type * as UiModule from "@/core/ui";

const harness = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/core/api", () => ({ api: harness }));
vi.mock("@/core/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof UiModule>();
  return { ...actual, useToast: () => ({ push: vi.fn() }) };
});

import { OpportunityApplicationPackageSection } from "./OpportunityApplicationPackageSection";

afterEach(cleanup);

it("links real derivatives and allows explicit sensitive answers without claiming readiness", async () => {
  harness.get.mockResolvedValue({
    readiness: "NEEDS_INPUT",
    updated_at: "2026-09-26T00:00:00Z",
    fact_verification: [],
    warnings: [],
    cv_change_audit: [],
    generated_documents: [{ document_id: "synthetic-doc", title: "Tailored CV", mime: "application/pdf" }],
    application_answers: [
      {
        question: "Do you require sponsorship?",
        classification: "sensitive_user_decision",
        proposed_answer: "",
        evidence_refs: [],
      },
    ],
  });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <OpportunityApplicationPackageSection opportunityId="synthetic-opportunity" online />
    </QueryClientProvider>,
  );
  await waitFor(() => expect(screen.getByText("Kullanıcı Girdisi Bekleniyor")).toBeTruthy());
  expect(screen.getByRole("link", { name: "Tailored CV (application/pdf)" }).getAttribute("href")).toBe(
    "/api/documents/synthetic-doc/file",
  );
  expect(screen.getByRole("textbox")).toBeTruthy();
  expect(screen.queryByText("Başvuruya Hazır")).toBeNull();
});

it("records explicit cover review without treating copy as approval", async () => {
  harness.get.mockResolvedValue({
    readiness: "NEEDS_INPUT",
    updated_at: "2026-09-26T00:00:00Z",
    fact_verification: [],
    warnings: [],
    cv_change_audit: [],
    generated_documents: [],
    application_answers: [],
    cover_letter: "Synthetic cover",
    cover_letter_review: { status: "pending", reviewed_at: null },
  });
  harness.post.mockResolvedValue({ readiness: "READY" });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <OpportunityApplicationPackageSection opportunityId="synthetic-opportunity" online />
    </QueryClientProvider>,
  );
  await waitFor(() => expect(screen.getByText("Kullanıcı Girdisi Bekleniyor")).toBeTruthy());
  fireEvent.click(screen.getByRole("button", { name: "Ön Yazı" }));
  expect(screen.getByText("İnsan incelemesi bekliyor")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Ön Yazıyı Onayla" }));
  await waitFor(() =>
    expect(harness.post).toHaveBeenCalledWith(
      "/opportunities/synthetic-opportunity/application-package/review-cover-letter",
      { decision: "approved" },
    ),
  );
});
