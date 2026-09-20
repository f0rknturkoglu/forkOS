/**
 * Konunun kanonik bilgi notu (Obsidian Vault).
 *
 * Kimlik konunun forkOS UUID'sidir; sunucu basligi ve dosya adini cozer.
 * Konu basina TEK yonetilen dosya vardir: `ensure` ikinci kez yeni dosya
 * uretmez, var olani dondurur.
 *
 * Govde forkOS'ta DUZENLENMEZ ve burada ikinci bir editor acilmaz. PHASE 2'de
 * tasinan eski notlar bilerek bu nota BIRLESTIRILMEDI; onlar Vault'ta ayri
 * dosyalar olarak durur, `Vault'ta ara` ile bulunur.
 */
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpen, ExternalLink, Plus, Search } from "lucide-react";
import { Button, SectionHeader, Skeleton, useToast } from "@/core/ui";
import { invalidateAfter } from "@/core/invalidation";
import {
  ensureVaultItem,
  getVaultItem,
  getVaultSearchUri,
  getVaultStatus,
  openObsidianUri,
  VAULT_ITEM_KEY,
  VAULT_STATUS_KEY,
  type VaultItem,
} from "@/core/obsidian";
import { useOnline } from "@/lib/hooks";

export function TopicKnowledgeNote({ topicId, topicTitle }: { topicId: string; topicTitle?: string }) {
  const online = useOnline();
  const toast = useToast();
  const [createdItem, setCreatedItem] = useState<VaultItem | null>(null);

  const { data: status, isLoading: isStatusLoading } = useQuery({
    queryKey: [VAULT_STATUS_KEY],
    queryFn: getVaultStatus,
  });
  const vaultReady = Boolean(status?.configured && status?.available);

  const { data: queryItem, isLoading: isItemLoading } = useQuery({
    queryKey: [VAULT_ITEM_KEY, topicId],
    queryFn: () => getVaultItem(topicId),
    enabled: vaultReady,
    retry: false,
  });
  const item = createdItem ?? queryItem;

  const create = useMutation({
    mutationFn: () => ensureVaultItem(topicId),
    onSuccess: (ensured) => {
      setCreatedItem(ensured);
      invalidateAfter("obsidian.write");
      toast.push("Bilgi notu Obsidian'da açıldı.", { tone: "ok" });
      openObsidianUri(ensured.open_uri);
    },
    onError: (error: Error) => toast.push(`Bilgi notu oluşturulamadı: ${error.message}`, { tone: "danger" }),
  });

  const search = useMutation({
    mutationFn: () => getVaultSearchUri(topicTitle ?? ""),
    onSuccess: ({ uri }) => openObsidianUri(uri),
    onError: (error: Error) => toast.push(`Vault'ta aranamadı: ${error.message}`, { tone: "danger" }),
  });

  if (isStatusLoading) {
    return (
      <div className="space-y-3">
        <SectionHeader label="Bilgi notu" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }

  if (!vaultReady) {
    return (
      <div className="space-y-3">
        <SectionHeader label="Bilgi notu" />
        <p className="text-meta text-muted">
          Vault kullanılamıyor —{" "}
          {!status?.configured
            ? "Obsidian Vault yapılandırılmamış (isteğe bağlı .env dosyasından açılabilir)."
            : "Obsidian Vault dizini mevcut değil veya erişilemiyor."}{" "}
          Bilgi notu bu yüzden açılamaz.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <SectionHeader label="Bilgi notu" hint="Obsidian'da yaşar" />

      <div className="rounded-card border border-subtle bg-surface px-3.5 py-3">
        {item ? (
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <BookOpen size={14} className="shrink-0 text-accent" />
                <p className="truncate font-medium text-primary">{item.title}</p>
              </div>
              <p className="mt-0.5 truncate text-meta text-muted">{item.relative_path}</p>
            </div>
            <a
              href={item.open_uri}
              className="inline-flex shrink-0 items-center gap-1.5 text-meta text-accent hover:underline"
              target="_blank"
              rel="noreferrer"
            >
              <ExternalLink size={13} /> Obsidian'da aç
            </a>
          </div>
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-meta text-muted">
              {isItemLoading ? "Not kontrol ediliyor…" : "Bu konu için henüz bir bilgi notu bağlanmadı."}
            </p>
            <Button size="sm" onClick={() => create.mutate()} disabled={!online || create.isPending || isItemLoading}>
              <Plus size={13} /> Bilgi notu oluştur
            </Button>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Tasinan eski notlar kanonik nota birlesmedi: Vault icinde ayri dururlar. */}
        <p className="text-meta text-muted">Eski notlar ayrı dosyalar olarak Vault'ta durur; aramayla bulunur.</p>
        <Button
          size="sm"
          disabled={!online || search.isPending || !topicTitle}
          onClick={() => search.mutate()}
          title={topicTitle ? undefined : "Aramak için konu başlığı gerekli"}
        >
          <Search size={13} /> Vault'ta ara
        </Button>
      </div>
    </div>
  );
}
