/**
 * A4 — Semantik Terfi & Dayanıklı Hafıza istemcisi.
 *
 * Epizodik ve kanonik kaynaklardan çıkan adayların inceleme, onay, ret ve terfi akışı.
 * f0rknbrain Vault'undaki 30 Knowledge/Memory/ kalıcı kartları ve forkOS durumunu yansıtır.
 */
import { api } from "@/core/api";
import type { components } from "@/generated/api-schema";

export const AGENT_SEMANTIC_STATUS_KEY = "agent-semantic-status";
export const AGENT_SEMANTIC_CANDIDATES_KEY = "agent-semantic-candidates";

export type SemanticStatus = components["schemas"]["SemanticStatusOut"];
export type SemanticCandidate = components["schemas"]["SemanticCandidateRead"];
export type SemanticCandidateList = components["schemas"]["SemanticCandidateListResponse"];
export type SemanticCandidateRefresh = components["schemas"]["SemanticCandidateRefreshOut"];
export type SemanticCandidatePromote = components["schemas"]["SemanticCandidatePromoteOut"];

export const getAgentSemanticStatus = () => api.get<SemanticStatus>("/agent/semantic/status");

export const listSemanticCandidates = (status?: string) =>
  api.get<SemanticCandidateList>(
    status ? `/agent/semantic/candidates?status=${encodeURIComponent(status)}` : "/agent/semantic/candidates",
  );

export const getSemanticCandidate = (id: string) => api.get<SemanticCandidate>(`/agent/semantic/candidates/${id}`);

export const refreshSemanticCandidates = () =>
  api.post<SemanticCandidateRefresh>("/agent/semantic/refresh", {
    include_episodes: true,
  });

export const confirmSemanticCandidate = (id: string, expected_revision: string) =>
  api.post<SemanticCandidate>(`/agent/semantic/candidates/${id}/confirm`, {
    expected_revision,
  });

export const rejectSemanticCandidate = (id: string, expected_revision: string) =>
  api.post<SemanticCandidate>(`/agent/semantic/candidates/${id}/reject`, {
    expected_revision,
  });

export const promoteSemanticCandidate = (
  id: string,
  expected_revision: string,
  target_destination?: string,
  supersedes?: string[],
) =>
  api.post<SemanticCandidatePromote>(`/agent/semantic/candidates/${id}/promote`, {
    expected_revision,
    target_destination,
    supersedes,
  });
