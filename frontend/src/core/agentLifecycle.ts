/** Yalnızca forkOS'un gözlediği içeriksiz oturum olayları; canlı bağlantı ölçümü değildir. */
import { api } from "@/core/api";

export const AGENT_LIFECYCLE_STATUS_KEY = "agent-lifecycle-status";

export interface AgentLifecycleStatus {
  available: boolean;
  last_event_at: string | null;
  last_harness: string | null;
  active_sessions: number;
  last_finalized_at: string | null;
  incomplete_session_count: number;
}

export const getAgentLifecycleStatus = () => api.get<AgentLifecycleStatus>("/agent/lifecycle/status");
