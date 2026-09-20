import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpen, ExternalLink, Plus } from "lucide-react";
import { Button, Section, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { createVaultItem, getVaultItem, getVaultStatus, type VaultItem } from "@/core/obsidian";
import type { Project } from "@/core/types";

export function ProjectKnowledgeNote({ project }: { project: Project }) {
  const online = useOnline();
  const toast = useToast();
  const [createdItem, setCreatedItem] = useState<VaultItem | null>(null);

  const { data: status } = useQuery({
    queryKey: ["obsidian-status"],
    queryFn: getVaultStatus,
  });

  const { data: queryItem, isLoading: isItemLoading } = useQuery({
    queryKey: ["obsidian-item", project.id],
    queryFn: () => getVaultItem(project.id),
    enabled: Boolean(status?.available),
    retry: false,
  });

  const item = createdItem ?? queryItem;

  const createNote = useMutation({
    mutationFn: () =>
      createVaultItem({
        forkos_id: project.id,
        forkos_type: "project",
        title: project.title,
        target_folder: "20 Projects",
      }),
    onSuccess: (created) => {
      setCreatedItem(created);
      toast.push("Obsidian proje notu oluşturuldu.", { tone: "ok" });
      if (created.open_uri) {
        window.open(created.open_uri, "_blank");
      }
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
