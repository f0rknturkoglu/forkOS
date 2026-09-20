import { api } from "@/core/api";

export interface VaultStatus {
  configured: boolean;
  available: boolean;
  writable: boolean;
  readable: boolean;
  vault_name: string;
  managed_files: number;
  conflicts: number;
  conflict_details: Record<string, string[]>;
  diagnostic: string | null;
}

export interface VaultItem {
  forkos_id: string;
  forkos_type: string;
  title: string;
  relative_path: string;
  open_uri: string;
  mtime: number;
  size: number;
}

export const getVaultStatus = () => api.get<VaultStatus>("/obsidian/status");
export const refreshVaultIndex = () => api.post<VaultStatus>("/obsidian/index/refresh", {});
export const getVaultItem = (id: string) => api.get<VaultItem>(`/obsidian/items/${id}`);
export const createVaultItem = (body: {
  forkos_id: string;
  forkos_type: string;
  title: string;
  target_folder?: string;
  initial_body?: string;
}) => api.post<VaultItem>("/obsidian/items", body);
