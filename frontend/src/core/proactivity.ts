/**
 * H6 proaktivite kontrol yuzeyi — kullaniciya donuk sozlesme.
 *
 * Iki ayri yuzey AYNI veriyi okur: Ayarlar > Proaktivite bolumu ve bildirim
 * panelindeki "Ertele" menusu. Kosu bicimi, query anahtarlari ve erteleme on
 * ayarlari tek yerde durur ki iki yuzey ayni seyi gostersin.
 *
 * Bu uclar canonical kaydi DEGISTIRMEZ: yalnizca motorun kendi
 * konfigurasyonunu ve erteleme durumunu yazar (bkz. backend
 * `app/modules/proactivity/router.py`).
 */
import { api } from "./api";

/** Query anahtarlari; tazeleme `invalidation.ts` icindeki `settings.write` ile olur. */
export const PROACTIVITY_STATUS_KEY = "proactivity-status";
export const PROACTIVITY_RULES_KEY = "proactivity-rules";
export const PROACTIVITY_HISTORY_KEY = "proactivity-history";

/**
 * `GET /proactivity/rules` satiri. `config` KAPALI semalidir: anahtarlari
 * kural turu belirler (`time`, `weekday`, `threshold_hours`, `days`,
 * `cooldown_days`, `grace_hours`).
 */
export interface ProactivityRule {
  kind: string;
  version: number;
  logical_key: string;
  enabled: boolean;
  config: Record<string, unknown>;
  snoozed_until: string | null;
}

/** Son kural hatasi: kural IZOLE duser, digerleri etkilenmez. */
interface ProactivityFailure {
  rule_kind: string | null;
  failure_code: string | null;
  at: string;
}

/**
 * `GET /proactivity/status` — sinirli durum ozeti (devasa gecmis dokumu degil).
 * Tuketiciler tipi ADIYLA anmadigi icin disa acilmaz; sekil `proactivityStatus`
 * donusunden cikarilir (olu export birakmama kurali).
 */
interface ProactivityStatus {
  enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  focus_deferral_enabled: boolean;
  digest_time: string;
  immediate_budget: number;
  immediate_surfaces_today: number;
  pending_deferred: number;
  pending_digest: number;
  /** `worker.heartbeat` ayari: `{ at }` — worker hic kosmadiysa `null`. */
  worker_heartbeat: { at?: string } | null;
  last_run_at: string | null;
  rules: ProactivityRule[];
  recent_failures: ProactivityFailure[];
}

/**
 * `GET /proactivity/history` satiri: TEK kosunun (episodun) yasam dongusu.
 * `state` backend'deki `RUN_STATES` kumesinden biridir. Tuketiciler adiyla
 * anmadigi icin disa acilmaz.
 */
interface ProactivityRun {
  id: number;
  rule_kind: string | null;
  subject_type: string | null;
  subject_id: string | null;
  state: string;
  reason_codes: string[];
  why_now: string | null;
  triggered_at: string;
  delivered_at: string | null;
  delivery_count: number;
  snoozed_until: string | null;
  /** Kosuyu yuzeye cikaran bildirim satiri; eslesme yoksa `null`. */
  notification_id: number | null;
  failure_code: string | null;
}

/** `PUT /proactivity/config` govdesi — yalniz bilinen alanlar. */
export interface ProactivityConfigPatch {
  enabled?: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  focus_deferral_enabled?: boolean;
  digest_time?: string;
}

/** `GET /proactivity/status` */
export const proactivityStatus = () => api.get<ProactivityStatus>("/proactivity/status");

/** `GET /proactivity/rules` */
export const proactivityRules = () => api.get<ProactivityRule[]>("/proactivity/rules");

/** `GET /proactivity/history` — varsayilan 50 satir (backend tavani). */
export const proactivityHistory = () => api.get<ProactivityRun[]>("/proactivity/history");

/** `PUT /proactivity/config` */
export const saveProactivityConfig = (patch: ProactivityConfigPatch) =>
  api.put<ProactivityStatus>("/proactivity/config", patch);

/** `PUT /proactivity/rules/{kind}` — ac/kapa ve esik ayari. */
export const saveProactivityRule = (kind: string, patch: { enabled?: boolean; config?: Record<string, unknown> }) =>
  api.put<ProactivityRule>(`/proactivity/rules/${kind}`, patch);

/** `POST /proactivity/runs/{id}/snooze` — kullanici override'i. */
export const snoozeProactivityRun = (runId: number, until: string) =>
  api.post<ProactivityRun[]>(`/proactivity/runs/${runId}/snooze`, { until });

/** `DELETE /proactivity/runs/{id}/snooze` — ertelemeyi kaldirir. */
export const unsnoozeProactivityRun = (runId: number) => api.del(`/proactivity/runs/${runId}/snooze`);

/** `POST /proactivity/rules/{kind}/snooze` — "bu hafta durtme". */
export const snoozeProactivityRule = (kind: string, until: string) =>
  api.post<ProactivityRule[]>(`/proactivity/rules/${kind}/snooze`, { until });

/** Erteleme on ayari: kullanici serbest zaman yazmaz, MUTLAK ISO uretilir (§108). */
export type SnoozePreset = "2h" | "tomorrow" | "3d" | "week";

/** Kosu menusundeki on ayarlar, en kisa once. */
export const SNOOZE_PRESETS: { id: SnoozePreset; label: string }[] = [
  { id: "2h", label: "2 saat sonra" },
  { id: "tomorrow", label: "Yarın sabah" },
  { id: "3d", label: "3 gün sonra" },
];

const HOUR_MS = 3_600_000;
const DAY_MS = 24 * HOUR_MS;

/**
 * On ayari mutlak ISO zamana cevirir. "Yarın sabah" YEREL saat 08:00'dir;
 * digerleri simdiki andan itibaren sabit suredir.
 */
export function snoozeUntil(preset: SnoozePreset, now: Date = new Date()): string {
  if (preset === "2h") return new Date(now.getTime() + 2 * HOUR_MS).toISOString();
  if (preset === "3d") return new Date(now.getTime() + 3 * DAY_MS).toISOString();
  if (preset === "week") return new Date(now.getTime() + 7 * DAY_MS).toISOString();
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(8, 0, 0, 0);
  return tomorrow.toISOString();
}
