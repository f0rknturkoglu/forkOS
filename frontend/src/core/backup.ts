import { api } from "@/core/api";

/**
 * Backup import sozlesmesi (Faz 16).
 *
 * `/backup/inspect` preflight'tir: hicbir sey yazmaz, yedegi inceler.
 * `/backup/restore` BIRLESTIREREK iceri aktarir (merge): ON CONFLICT
 * DO NOTHING, mevcut kayitlara dokunulmaz. Tam geri donus (disaster
 * restore) app disidir -- make disaster-restore.
 */

export interface BackupInspect {
  version: number;
  app: string | null;
  exported_at: string | null;
  table_counts: {
    entities: number;
    links: number;
    events: number;
    modules: Record<string, number>;
  };
  unknown_tables: string[];
  missing_sections: string[];
  secret_settings: number;
  integrity_ok: boolean | null;
}

export interface BackupMergeResult {
  restored: number;
  skipped: number;
  tables: Record<string, { inserted: number; skipped: number; secret_skipped?: number }>;
}

export const inspectBackup = (file: File) => api.upload<BackupInspect>("/backup/inspect", file);
export const mergeRestore = (file: File) => api.upload<BackupMergeResult>("/backup/restore", file);
