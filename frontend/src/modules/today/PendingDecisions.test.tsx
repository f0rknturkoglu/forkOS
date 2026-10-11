// @vitest-environment jsdom
/**
 * "Bekleyen kararlar" (H7) sozlesmesi. Gercek ag yok: `fetch` kaydedici bir
 * stub'dur; hangi ucun hangi govdeyle cagrildigi burada dogrulanir.
 *
 * Kapsanan kurallar:
 *  - bos liste hicbir sey cizmez (karar yuzeyi gunun akisina gurultu eklemez)
 *  - satir adim/mutasyon sayisini ve son gecerliligi gosterir
 *  - "Onayla" TAM olarak goruntulenen revizyonu gonderir (sunucu eski
 *    revizyona verilen onayi APPROVAL_STALE ile reddeder)
 *  - onaydan sonra birincil buton "Yürüt" olur; yurutme sonrasi adim
 *    makbuzlari ve nihai durum gorunur
 *  - karar kabul etmeyen (terminal) plana karar butonu SUNULMAZ
 */

import { QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ExecutionPlanView, ExecutionReceiptView } from "@/core/execution";
import { queryClient } from "@/core/queryClient";
import { PendingDecisions, PlanReviewModal } from "./PendingDecisions";

const REVISION = "plan-v1:9f2c1d4b7a6e5c3f0b9d8a7c6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f";
const TODO_ID = "11111111-2222-3333-4444-555555555555";
const EVENT_REF = "event:99999999-8888-7777-6666-555555555555";

interface Call {
  method: string;
  path: string;
  search: string;
  body?: Record<string, unknown>;
}

let calls: Call[] = [];
/** Liste yaniti (bekleyen planlar). */
let pending: ExecutionPlanView[];
/** Detay yaniti; POST'lar bunu gercek backend gibi gunceller. */
let plan: ExecutionPlanView;

function json(value: unknown): Response {
  return new Response(JSON.stringify(value), { status: 200, headers: { "Content-Type": "application/json" } });
}

function inHours(hours: number): string {
  return new Date(Date.now() + hours * 3_600_000).toISOString();
}

function planView(overrides: Partial<ExecutionPlanView> = {}): ExecutionPlanView {
  return {
    plan_row_id: 7,
    plan_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    revision: REVISION,
    is_current_revision: true,
    state: "awaiting_approval",
    title: "Haftalık odak planı",
    summary: "İki görevi bu haftaya taşır.",
    reason: "projede 16 gündür kayıtlı anlamlı aktivite yok",
    steps: [
      {
        step_id: "s1",
        action: "todo_update",
        arguments: { todo_id: TODO_ID, status: "planned" },
        description: "Görevi plana al",
        expected_updated_at: "2026-09-20T09:00:00+00:00",
      },
    ],
    step_count: 1,
    mutation_count: 1,
    budget: { max_steps: 10, max_mutations: 10, steps: 1 },
    source_refs: [`entity:${TODO_ID}`],
    evidence_refs: [EVENT_REF],
    verified_refs: [],
    unresolved_refs: [],
    validation_status: "valid",
    validation_errors: [],
    input_questions: [],
    input_answers: {},
    approved_revision: null,
    approved_at: null,
    expires_at: inHours(72),
    decision_required: true,
    final_status: null,
    failure_code: null,
    receipts: [],
    created_at: "2026-09-21T06:00:00+00:00",
    updated_at: "2026-09-21T06:00:00+00:00",
    ...overrides,
  };
}

/** Adim makbuzu: backend `_plan_view` sekli (sadelestirilmis alanlar dahil). */
function receipt(overrides: Partial<ExecutionReceiptView>): ExecutionReceiptView {
  return {
    step_id: "s1",
    ordinal: 0,
    action: "todo_update",
    target: TODO_ID,
    status: "completed",
    error_code: null,
    result_ref: null,
    completed_at: "2026-09-21T07:00:01+00:00",
    ...overrides,
  };
}

/** Onay + yurutme sonrasi: ilk adim stale, ikincisi hic denenmedi. */
function executedPlan(): ExecutionPlanView {
  return planView({
    state: "partial",
    decision_required: false,
    approved_revision: REVISION,
    approved_at: "2026-09-21T07:00:00+00:00",
    final_status: "partial",
    failure_code: "STEP_STALE",
    receipts: [
      receipt({ status: "failed", error_code: "STEP_STALE", result_ref: null }),
      receipt({
        step_id: "s2",
        ordinal: 1,
        action: "todo_complete",
        status: "not_attempted",
        error_code: null,
        completed_at: null,
      }),
    ],
  });
}

function renderWidget() {
  return render(
    <QueryClientProvider client={queryClient()}>
      <PendingDecisions />
    </QueryClientProvider>,
  );
}

function lastCall(method: string, path: string): Call | undefined {
  return [...calls].reverse().find((call) => call.method === method && call.path === path);
}

beforeEach(() => {
  // Yuzey `invalidateAfter` ile tazelenir; o da PAYLASILAN istemciyi kullanir.
  queryClient().clear();
  queryClient().setDefaultOptions({ queries: { retry: false, staleTime: 0 } });
  calls = [];
  plan = planView();
  pending = [plan];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const method = (init?.method ?? "GET").toUpperCase();
      calls.push({
        method,
        path: url.pathname,
        search: url.search,
        body: init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined,
      });

      if (method === "GET" && url.pathname === "/api/execution/plans") return json(pending);
      if (method === "GET" && url.pathname === `/api/execution/plans/${plan.plan_row_id}`) return json(plan);
      // Kararlar yalnizca plan DURUMUNU degistirir; onaydan sonra plan
      // bekleyen listesinden cikar (gercek sunucu davranisi).
      if (method === "POST" && url.pathname.endsWith("/approve")) {
        plan = planView({
          ...plan,
          state: "approved",
          approved_revision: plan.revision,
          approved_at: "2026-09-21T07:00:00+00:00",
          decision_required: false,
        });
        pending = [];
        return json(plan);
      }
      if (method === "POST" && (url.pathname.endsWith("/execute") || url.pathname.endsWith("/recover"))) {
        plan = executedPlan();
        return json(plan);
      }
      if (method === "POST" && url.pathname.endsWith("/respond")) {
        plan = { ...plan, state: "draft", decision_required: false };
        pending = [];
        return json(plan);
      }
      return json({});
    }),
  );
});

it("one apply interaction records approval before executing the exact displayed revision", async () => {
  render(
    <QueryClientProvider client={queryClient()}>
      <PlanReviewModal planRowId={7} onClose={() => {}} applyTogether />
    </QueryClientProvider>,
  );
  fireEvent.click(await screen.findByRole("button", { name: "Değişiklikleri uygula" }));
  await screen.findAllByText(/STEP_STALE/);
  expect(calls.filter((call) => call.method === "POST").map((call) => [call.path, call.body])).toEqual([
    ["/api/execution/plans/7/approve", { revision: REVISION }],
    ["/api/execution/plans/7/execute", { revision: REVISION }],
  ]);
});

it("stale execution exposes receipt reconciliation instead of another execute", async () => {
  plan = planView({ state: "executing", needs_recovery: true, decision_required: false, approved_revision: REVISION });
  render(
    <QueryClientProvider client={queryClient()}>
      <PlanReviewModal planRowId={7} onClose={() => {}} />
    </QueryClientProvider>,
  );
  const recover = await screen.findByRole("button", { name: "Makbuzları denetleyip devam et" });
  expect(screen.queryByRole("button", { name: "Yürüt" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Onayla" })).toBeNull();
  fireEvent.click(recover);
  await waitFor(() => expect(lastCall("POST", "/api/execution/plans/7/recover")).toBeTruthy());
  expect(lastCall("POST", "/api/execution/plans/7/execute")).toBeUndefined();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("Bekleyen kararlar", () => {
  it("bekleyen plan yokken bolumu hic cizmez", async () => {
    pending = [];
    const { container } = renderWidget();

    await waitFor(() => expect(calls.some((call) => call.path === "/api/execution/plans")).toBe(true));
    // Yalnizca karar bekleyen durumlar sorulur: terminal planlar bu yuzeyin isi degil.
    expect(decodeURIComponent(lastCall("GET", "/api/execution/plans")?.search ?? "")).toBe(
      "?states=awaiting_approval,input_required",
    );
    expect(container.innerHTML).toBe("");
  });

  it("plan satirini adim/mutasyon sayisi, son gecerlilik ve durumla gosterir", async () => {
    renderWidget();

    expect(await screen.findByText("1 plan kararını bekliyor")).toBeTruthy();
    expect(screen.getByText("Haftalık odak planı")).toBeTruthy();
    expect(screen.getByText("1 adım · 1 mutasyon")).toBeTruthy();
    expect(screen.getByText("3 gün içinde doluyor")).toBeTruthy();
    expect(screen.getByText("Onay bekliyor")).toBeTruthy();
  });

  it("inceleme modali neden, kanit, adim, revizyon ve son gecerliligi gosterir", async () => {
    renderWidget();
    fireEvent.click(await screen.findByText("Haftalık odak planı"));

    expect(await screen.findByText("projede 16 gündür kayıtlı anlamlı aktivite yok")).toBeTruthy();
    // Kanit referanslari kisaltilir; tamami title'da kalir.
    expect(screen.getByTitle(EVENT_REF)).toBeTruthy();
    expect(screen.getByText("todo_update")).toBeTruthy();
    expect(screen.getByText("Görevi plana al")).toBeTruthy();
    expect(screen.getByText("hedef 11111111-222…")).toBeTruthy();
    expect(screen.getByText("plan-v1:9f2c1d4b7a…")).toBeTruthy();
    expect(screen.getByText("İki görevi bu haftaya taşır.")).toBeTruthy();
  });

  it("Onayla, goruntulenen revizyonla onay ucuna gider", async () => {
    renderWidget();
    fireEvent.click(await screen.findByText("Haftalık odak planı"));
    fireEvent.click(await screen.findByRole("button", { name: "Onayla" }));

    await waitFor(() => {
      expect(lastCall("POST", "/api/execution/plans/7/approve")?.body).toEqual({ revision: REVISION });
    });
  });

  it("onaydan sonra birincil buton Yürüt olur; sonuc makbuzlari gorunur", async () => {
    renderWidget();
    fireEvent.click(await screen.findByText("Haftalık odak planı"));
    fireEvent.click(await screen.findByRole("button", { name: "Onayla" }));

    // Onay bekleyen plan listeden dusse de inceleme modali acik kalir.
    const run = await screen.findByRole("button", { name: "Yürüt" });
    expect(screen.queryByRole("button", { name: "Onayla" })).toBeNull();

    fireEvent.click(run);
    await waitFor(() => {
      expect(lastCall("POST", "/api/execution/plans/7/execute")?.body).toEqual({ revision: REVISION });
    });

    expect(await screen.findByText("Nihai durum: Kısmi")).toBeTruthy();
    // Hata kodu hem nihai durumda hem basarisiz adimin makbuzunda gorunur.
    expect(screen.getAllByText("STEP_STALE")).toHaveLength(2);
    expect(screen.getByText("todo_complete")).toBeTruthy();
    expect(screen.getByText("not_attempted")).toBeTruthy();
    // Terminal sonuc: yeni karar butonu sunulmaz.
    expect(screen.queryByRole("button", { name: "Yürüt" })).toBeNull();
    expect(screen.queryByRole("button", { name: "İptal" })).toBeNull();
  });

  it("karar kabul etmeyen planlarda karar butonu gostermez", async () => {
    for (const state of ["expired", "rejected"] as const) {
      plan = planView({ state, decision_required: false });
      pending = [plan];
      const { unmount } = renderWidget();

      fireEvent.click(await screen.findByText("Haftalık odak planı"));
      // Modal adim aciklamasiyla acildi mi (terminal planda footer yok).
      expect(await screen.findByText("Görevi plana al")).toBeTruthy();
      expect(screen.queryByRole("button", { name: "Onayla" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Reddet" })).toBeNull();
      expect(screen.queryByRole("button", { name: "İptal" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Yürüt" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Yanıtla" })).toBeNull();
      unmount();
      cleanup();
    }
  });

  it("eksik bilgi planinda cevaplar soruyla anahtarlanip yanit ucuna gider", async () => {
    const question = "Hangi görevi plana alalım?";
    plan = planView({ state: "input_required", input_questions: [question] });
    pending = [plan];
    renderWidget();

    fireEvent.click(await screen.findByText("Haftalık odak planı"));
    // Reddet yalnizca onay bekleyen planda gecerlidir; burada sunulmaz.
    expect(screen.queryByRole("button", { name: "Reddet" })).toBeNull();
    const submit = await screen.findByRole("button", { name: "Yanıtla" });
    expect((submit as HTMLButtonElement).disabled).toBe(true);

    fireEvent.change(screen.getByLabelText(question), { target: { value: "Haftalık odak" } });
    fireEvent.click(await screen.findByRole("button", { name: "Yanıtla" }));

    await waitFor(() => {
      expect(lastCall("POST", "/api/execution/plans/7/respond")?.body).toEqual({
        answers: { [question]: "Haftalık odak" },
      });
    });
  });
});
