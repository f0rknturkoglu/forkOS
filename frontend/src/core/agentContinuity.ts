/**
 * Agent bağlam ve kaynak devamlılığı tanılamaları.
 *
 * Ephemeral oturum bağlamı ve teslim edilen kaynakların durumunu sorgular.
 * Canlı bağlantı veya model sahipliği iddiası taşımaz.
 */
import { api } from "@/core/api";

export const AGENT_CONTINUITY_STATUS_KEY = "agent-continuity-status";

interface AgentContinuityStatus {
  available: boolean;
  last_bootstrap_at: string | null;
  last_context_at: string | null;
  last_harness: string | null;
  active_source_count: number;
  is_truncated: boolean;
  degraded_reasons: string[];
  has_active_continuity: boolean;
}

export const getAgentContinuityStatus = () => api.get<AgentContinuityStatus>("/agent/continuity/status");
