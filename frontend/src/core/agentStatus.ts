/**
 * Brain & Agent tanılama yüzeyi (istemci tarafı).
 *
 * Bu modül forkOS'un NELERİ bildiğini ve NEYİ bilemeyeceğini tek yerde
 * toplar: Brain Interface metadata'sı (MCP sunucusu, uç, H0–H7 aileleri) ve
 * H4 yerel biliş durumu sunucudan gelir. Tarayıcı modele DOKUNMAZ; ölçüm
 * sunucuda, sınırlı bir loopback yoklamasıyla yapılır.
 *
 * Hermes'in istemci tarafı durumu (trust, seçili model, oturum) BURADA YOKTUR
 * ve olamaz: forkOS onu doğrulayamaz (§ E). "Hermes bağlı" gibi bir alan
 * üretmek yalan bir söz olurdu.
 */
import { api } from "@/core/api";

/** Sorgu anahtarı: Brain tanılaması yalnız bununla tazelenir. */
export const AGENT_STATUS_KEY = "agent-status";

/** H0–H7 ailelerinden biri: kimlik, insan dili etiket ve araç sayısı. */
export interface BrainFamilyView {
  id: string;
  label: string;
  summary: string;
  tool_count: number;
}

/** `GET /agent/status` → `brain`: MCP sunucusunun gerçek kayıt durumu. */
export interface BrainStatusView {
  server_name: string;
  /** Sunucunun kendi bildirdiği loopback ucu (istemci birleştirmez). */
  endpoint: string;
  transport: string;
  loopback_only: boolean;
  tool_count: number;
  families: BrainFamilyView[];
}

/** Bir H4 yuvasının (small/medium) yapılandırma ve varlık durumu. */
export interface LocalCognitionSlotView {
  configured: boolean;
  available: boolean;
}

/**
 * H4 durum kümesi (backend `state` alanı ile aynı):
 *  - `disabled`             : H4 kapalı; bu geçerli ve sağlıklı bir durumdur.
 *  - `not_configured`       : açık ama model kimliği yazılmamış.
 *  - `provider_unreachable` : Ollama erişilemiyor ya da adres loopback dışı.
 *  - `model_missing`        : sağlayıcı ayakta, yapılandırılan model kurulu değil.
 *  - `ready`                : sağlayıcı erişilebilir ve modeller kurulu.
 */
export type LocalCognitionState = "disabled" | "not_configured" | "provider_unreachable" | "model_missing" | "ready";

/** H4 yerel biliş — Hermes'in sohbet modelinden BAĞIMSIZ forkOS katmanı. */
export interface LocalCognitionView {
  enabled: boolean;
  provider: string;
  /** `loopback` ya da `invalid`: güvenlik değişmezi yapılandırmada görünür. */
  endpoint_class: "loopback" | "invalid";
  configured: boolean;
  /** Yalnız yoklama yapıldıysa dolu; H4 kapalıyken `null`. */
  reachable: boolean | null;
  state: LocalCognitionState;
  small: LocalCognitionSlotView;
  medium: LocalCognitionSlotView;
  /** Sınırlı, kullanıcıya gösterilebilir açıklama; sır ya da yol içermez. */
  detail: string | null;
}

/**
 * `GET /agent/status` gövdesi: iki bağımsız tanılama bloğu.
 *
 * Dışa AÇILMAZ: bugün hiçbir tüketici bu tipi adıyla anmıyor (`brain` ve
 * `local_cognition` parçaları kullanılır); ölü export bırakmama kuralı.
 */
interface AgentStatus {
  brain: BrainStatusView;
  local_cognition: LocalCognitionView;
}

/** Tek okuma: Brain Interface metadata'sı + H4 durumu (mutasyon yok). */
export const getAgentStatus = () => api.get<AgentStatus>("/agent/status");

/**
 * Beyin yüzeyinin okunabilir durumu. `unavailable` istek hatası, `degraded`
 * ise uç loopback'e bağlı OLMADIĞI anlamına gelir: çalışıyor ama yerel sınır
 * kalkmış. Bu ayrım kullanıcıya gösterilir, gizlenmez.
 */
export type BrainReadiness = "ready" | "degraded" | "unavailable";

export function brainReadiness(status: AgentStatus["brain"] | undefined, isError: boolean): BrainReadiness {
  if (isError || !status || status.tool_count <= 0) return "unavailable";
  return status.loopback_only ? "ready" : "degraded";
}
