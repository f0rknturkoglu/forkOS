/**
 * A3 — son oturum devri tanılaması.
 *
 * Yalnızca mühürlenmiş epizodun METADATA'sını sorgular: ham konuşma, ifade
 * metni veya devir içeriği taşımaz. Hermes istemcisinin bağlı olduğunu da
 * iddia etmez; yalnız forkOS'un kendi kaydını raporlar.
 */
import { api } from "@/core/api";
import type { components } from "@/generated/api-schema";

export const AGENT_EPISODE_STATUS_KEY = "agent-episode-status";

type AgentEpisodeStatus = components["schemas"]["EpisodeStatusOut"];

export const getAgentEpisodeStatus = () => api.get<AgentEpisodeStatus>("/agent/episode/status");
