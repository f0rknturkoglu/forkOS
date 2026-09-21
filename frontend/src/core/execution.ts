/**
 * H7 — dayanikli karar ve sinirli yurutme (kullaniciya donuk sozlesme).
 *
 * Uc is yapar, UCU DE canonical mutasyon DEGILDIR:
 *
 *   inceleme  list/get                 -> planin KENDISI (adim + kanit + revizyon)
 *   karar     approve/reject/respond/cancel -> yalnizca plan durumu
 *   yurutme   execute                  -> onayli TAM revizyonu H1 uzerinden uygular
 *
 * Bu yuzden burada "plani duzenle" diye bir uc YOKTUR: plan IMMUTABLE bir
 * revizyondur (`plan-v1:<sha256>`), icerik degisikligi YENI revizyon demektir
 * ve onu Hermes hazirlar. Onay sunucu tarafinda bir KAYITTIR ve her zaman bir
 * revizyona baglanir; bu yuzden approve/execute cagrilari revizyonu acikca
 * gonderir (eski revizyona verilen onay `APPROVAL_STALE` ile reddedilir).
 *
 * Backend: `app/modules/execution/router.py` (REST), `state.py` (durum
 * makinesi), `service.py::_plan_view` (govde sekli).
 */
import { api, qs } from "./api";

/** Karar bekleyen durumlar — "Bekleyen kararlar" yuzeyi yalniz bunlari sorar. */
const PENDING_PLAN_STATES = ["awaiting_approval", "input_required"];

/** `PLAN_STATES` (models.py) ile ayni kume. */
export type ExecutionPlanState =
  | "draft"
  | "validating"
  | "input_required"
  | "awaiting_approval"
  | "approved"
  | "executing"
  | "completed"
  | "partial"
  | "failed"
  | "rejected"
  | "cancelled"
  | "expired";

/** KAPALI H1 aksiyon sozlugunden bir adim (`steps.py::step_payload`). */
export interface ExecutionStepView {
  step_id: string;
  /** `write_registry.ACTION_NAMES` icinden; serbest arac adi DEGIL. */
  action: string;
  /** H1 girdi modelinin normalize ettigi govde. */
  arguments: Record<string, unknown>;
  description: string;
  /** Onay bu damgaya baglanir; hedef sonradan degisirse adim `STEP_STALE` olur. */
  expected_updated_at: string | null;
}

/** Adim basina TEK makbuz (`execution_receipt`). */
export interface ExecutionReceiptView {
  step_id: string;
  ordinal: number;
  action: string;
  target: string | null;
  /** `completed` | `failed` | `skipped` | `not_attempted`. */
  status: string;
  /** `STEP_STALE`, `RECONCILIATION_REQUIRED`, H1 hata kodu ... yoksa `null`. */
  error_code: string | null;
  /** H1 sonucundan gelen sinirli referans (tam govde degil). */
  result_ref: string | null;
  completed_at: string | null;
}

/** `GET /execution/plans` ve `GET /execution/plans/{id}` satiri. */
export interface ExecutionPlanView {
  plan_row_id: number;
  /** Soy agaci kimligi: revizyonlar bu degeri paylasir. */
  plan_id: string;
  revision: string;
  /** Bu satir planin EN GUNCEL revizyonu mu (onay bayatligi buradan okunur). */
  is_current_revision: boolean;
  state: ExecutionPlanState;
  title: string;
  summary: string | null;
  /** "Neden bu plan var?" — olgusal, sinirli. */
  reason: string | null;
  steps: ExecutionStepView[];
  step_count: number;
  mutation_count: number;
  budget: Record<string, number>;
  source_refs: string[];
  evidence_refs: string[];
  validation_status: string;
  validation_errors: { code: string; message: string; step_id?: string | null }[];
  /** `input_required` durumunda kullaniciya sorulan sinirli sorular. */
  input_questions: string[];
  input_answers: Record<string, string>;
  approved_revision: string | null;
  approved_at: string | null;
  expires_at: string | null;
  decision_required: boolean;
  final_status: string | null;
  failure_code: string | null;
  receipts: ExecutionReceiptView[];
  created_at: string;
  updated_at: string;
}

/**
 * `state.py::ALLOWED_TRANSITIONS` ile AYNI tablo. Karar butonlari buradan
 * turetilir: sunucunun reddedecegi bir gecisi kullaniciya sunmak yanlis soz
 * vermek olur (or. `input_required` planina "Reddet" gostermek).
 */
const ALLOWED_TRANSITIONS: Record<ExecutionPlanState, readonly ExecutionPlanState[]> = {
  draft: ["validating", "input_required", "cancelled", "expired"],
  validating: ["awaiting_approval", "input_required", "expired"],
  input_required: ["draft", "cancelled", "expired"],
  awaiting_approval: ["approved", "rejected", "cancelled", "expired"],
  // Onaydan sonra revizyon DEGISMEZ: yalnizca yurutme ya da iptal.
  approved: ["executing", "cancelled", "expired"],
  executing: ["completed", "partial", "failed"],
  completed: [],
  partial: [],
  failed: [],
  rejected: [],
  cancelled: [],
  expired: [],
};

/** Durum etiketi (rozet ve baslik metinleri tek yerden). */
export const PLAN_STATE_LABELS: Record<ExecutionPlanState, string> = {
  draft: "Taslak",
  validating: "Doğrulanıyor",
  input_required: "Yanıt bekliyor",
  awaiting_approval: "Onay bekliyor",
  approved: "Onaylandı",
  executing: "Yürütülüyor",
  completed: "Tamamlandı",
  partial: "Kısmi",
  failed: "Başarısız",
  rejected: "Reddedildi",
  cancelled: "İptal edildi",
  expired: "Süresi doldu",
};

/** `current → target` geçişi sunucuda izinli mi? Bilinmeyen durumda `false`. */
export function canTransition(current: ExecutionPlanState, target: ExecutionPlanState): boolean {
  return (ALLOWED_TRANSITIONS[current] ?? []).includes(target);
}

/** `GET /execution/plans?states=awaiting_approval,input_required` */
export const pendingExecutionPlans = () =>
  api.get<ExecutionPlanView[]>(`/execution/plans${qs({ states: PENDING_PLAN_STATES.join(",") })}`);

/** `GET /execution/plans/{id}` — makbuzlar ve nihai durum yalniz burada gelir. */
export const fetchExecutionPlan = (planRowId: number) => api.get<ExecutionPlanView>(`/execution/plans/${planRowId}`);

/** `POST /execution/plans/{id}/approve` — sunucu tarafi onay kaydi. */
export const approveExecutionPlan = (planRowId: number, revision: string) =>
  api.post<ExecutionPlanView>(`/execution/plans/${planRowId}/approve`, { revision });

/** `POST /execution/plans/{id}/reject` */
export const rejectExecutionPlan = (planRowId: number) =>
  api.post<ExecutionPlanView>(`/execution/plans/${planRowId}/reject`, {});

/**
 * `POST /execution/plans/{id}/respond` — cevap MUTASYON URETMEZ: plan
 * `draft`'a doner ve yeniden hazirlanir (yeni revizyon → yeni onay).
 */
export const respondExecutionPlan = (planRowId: number, answers: Record<string, string>) =>
  api.post<ExecutionPlanView>(`/execution/plans/${planRowId}/respond`, { answers });

/** `POST /execution/plans/{id}/cancel` */
export const cancelExecutionPlan = (planRowId: number) =>
  api.post<ExecutionPlanView>(`/execution/plans/${planRowId}/cancel`, {});

/** `POST /execution/plans/{id}/execute` — YALNIZ onayli revizyon yurutulur. */
export const runExecutionPlan = (planRowId: number, revision: string) =>
  api.post<ExecutionPlanView>(`/execution/plans/${planRowId}/execute`, { revision });
