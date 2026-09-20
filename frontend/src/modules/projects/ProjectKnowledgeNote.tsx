import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, BookOpen, ExternalLink, Plus } from "lucide-react";
import { Button, Section, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { ApiError } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import {
  ensureVaultItem,
  getVaultItem,
  getVaultStatus,
  openObsidianUri,
  VAULT_ITEM_KEY,
  VAULT_STATUS_KEY,
  type VaultItem,
} from "@/core/obsidian";
import type { Project } from "@/core/types";

/**
 * Projenin kanonik bilgi notu (Obsidian Vault).
 *
 * Kimlik projenin forkOS UUID'sidir: sunucu basligi, klasoru ve tipini
 * kendisi cozer. Istemci yalnizca "bu kimlik icin not var mi" sorusunu
 * sorar; yoksa `ensure` ile olusturur. Govde forkOS'ta DUZENLENMEZ --
 * yazma yuzeyi Obsidian'in kendisidir.
 */
export function ProjectKnowledgeNote({ project }: { project: Project }) {
  const online = useOnline();
  const toast = useToast();
  const [createdItem, setCreatedItem] = useState<VaultItem | null>(null);

  const { data: status } = useQuery({
    queryKey: [VAULT_STATUS_KEY],
    queryFn: getVaultStatus,
  });

  const {
    data: queryItem,
    isLoading: isItemLoading,
    error: itemError,
  } = useQuery({
    queryKey: [VAULT_ITEM_KEY, project.id],
    queryFn: () => getVaultItem(project.id),
    enabled: Boolean(status?.available),
    retry: false,
  });

  const item = createdItem ?? queryItem;

  const conflictPaths = status?.conflict_details?.[project.id];
  const isConflicted = Boolean(conflictPaths || (itemError instanceof ApiError && itemError.status === 409));

  const createNote = useMutation({
    mutationFn: () => ensureVaultItem(project.id),
    onSuccess: (created) => {
      setCreatedItem(created);
      invalidateAfter("obsidian.write");
      toast.push("Obsidian proje notu oluşturuldu.", { tone: "ok" });
      openObsidianUri(created.open_uri);
    },
    onError: (err: Error) => {
      toast.push(`Proje notu oluşturulamadı: ${err.message}`, { tone: "danger" });
    },
  });

  // Eğer Vault yapılandırılmamışsa veya erişilemiyorsa sade bilgilendirme
  if (!status?.configured || !status?.available) {
    return (
      <Section title="Bilgi notu">
        <div className="flex items-center justify-between gap-3 text-meta text-muted">
          <div className="flex items-center gap-2">
            <BookOpen size={14} className="text-muted" />
            <span>
              {!status?.configured
                ? "Obsidian Vault yapılandırılmamış (isteğe bağlı .env dosyasından açılabilir)."
                : "Obsidian Vault dizini mevcut değil veya erişilemiyor."}
            </span>
          </div>
        </div>
      </Section>
    );
  }

  // Çakışma durumu: aynı forkos_id birden fazla dosyada mevcutsa fail-closed göster
  if (isConflicted) {
    return (
      <Section title="Bilgi notu">
        <div className="rounded-control border border-danger-border bg-danger-surface p-3 text-meta">
          <div className="flex items-start gap-2 text-danger">
            <AlertTriangle size={15} className="mt-0.5 shrink-0" />
            <div className="space-y-1">
              <p className="font-medium">
                Bu kimlik birden fazla Obsidian dosyasında kullanılıyor. Çakışmayı Vault içinde çöz ve indeksi yenile.
              </p>
              {conflictPaths && conflictPaths.length > 0 && (
                <ul className="list-disc list-inside text-micro text-danger/80 font-mono space-y-0.5 mt-1">
                  {conflictPaths.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </Section>
    );
  }

  return (
    <Section title="Bilgi notu">
      {item ? (
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <BookOpen size={14} className="text-accent" />
              <p className="font-medium text-primary truncate">{item.title}</p>
            </div>
            <p className="text-meta text-muted truncate mt-0.5">{item.relative_path}</p>
          </div>
          <a
            href={item.open_uri}
            className="inline-flex items-center gap-1.5 text-meta text-accent hover:underline shrink-0"
            target="_blank"
            rel="noreferrer"
          >
            <ExternalLink size={13} /> Obsidian'da aç
          </a>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-meta text-muted">
            {isItemLoading ? "Not kontrol ediliyor…" : "Bu proje için henüz bir Obsidian notu bağlanmadı."}
          </p>
          <Button
            size="sm"
            onClick={() => createNote.mutate()}
            disabled={!online || createNote.isPending || isItemLoading}
          >
            <Plus size={13} /> Obsidian proje notu oluştur
          </Button>
        </div>
      )}
    </Section>
  );
}
