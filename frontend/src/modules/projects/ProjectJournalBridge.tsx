import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpen } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { getVaultStatus, openObsidianUri, VAULT_STATUS_KEY, type VaultItem } from "@/core/obsidian";
import { Button, Field, Input, Section, Skeleton, useToast } from "@/core/ui";
import { keyToUtc, todayKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";

function dayLabel(day: string): string {
  return keyToUtc(day).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

/**
 * Proje gunlugunun Vault koprusu.
 *
 * Gunluk GOVDESI forkOS'ta DURMAZ: burada editor yok. Aksiyon, secilen gunun
 * Vault dosyasini cozer/olusturur (`ensure` semantigi) ve Obsidian'da acar.
 * Gelecek gun secilemez; sunucu da reddeder.
 */
export function ProjectJournalBridge({ projectId }: { projectId: string }) {
  const today = todayKey();
  const online = useOnline();
  const toast = useToast();
  const [day, setDay] = useState(today);

  useEffect(() => {
    setDay(today);
  }, [projectId, today]);

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: [VAULT_STATUS_KEY],
    queryFn: getVaultStatus,
  });

  const openJournal = useMutation({
    mutationFn: (target: string) => api.post<VaultItem>(`/projects/${projectId}/journal/${target}/obsidian`, {}),
    onSuccess: (item) => {
      invalidateAfter("obsidian.write");
      openObsidianUri(item.open_uri);
      toast.push(`${dayLabel(item.journal_day ?? day)} günlüğü Obsidian'da açıldı.`, { tone: "ok" });
    },
    onError: (error: Error) => {
      toast.push(`Proje günlüğü açılamadı: ${error.message}`, { tone: "danger" });
    },
  });

  const vaultReady = Boolean(status?.configured && status?.available);

  return (
    <Section title="Günlük" hint="günlük notu Obsidian'da yaşar" bodyClassName="space-y-3">
      {statusLoading ? (
        <Skeleton className="h-10 w-full" />
      ) : !vaultReady ? (
        <p className="text-meta text-muted">
          Vault kullanılamıyor —{" "}
          {!status?.configured
            ? "Obsidian Vault yapılandırılmamış (isteğe bağlı .env dosyasından açılabilir)."
            : "Obsidian Vault dizini mevcut değil veya erişilemiyor."}{" "}
          Günlük notu bu yüzden açılamaz.
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-end gap-3">
            <Field label="Günlük günü" className="w-full sm:w-48">
              <Input
                type="date"
                value={day}
                max={today}
                onChange={(value) => {
                  if (value && value <= today) setDay(value);
                }}
                ariaLabel="Günlük günü"
                className="w-full bg-surface"
              />
            </Field>
            <Button
              variant="primary"
              disabled={!online || openJournal.isPending}
              onClick={() => openJournal.mutate(day)}
            >
              <BookOpen size={14} />
              {day === today ? "Bugünün proje günlüğünü Obsidian'da aç" : "Seçili günün günlüğünü Obsidian'da aç"}
            </Button>
          </div>
          <p className="text-meta text-muted">
            Gelecek bir gün seçilemez. Günlük metni Obsidian'da yazılır; forkOS notu açar, içeriğin kopyasını tutmaz.
          </p>
        </>
      )}
    </Section>
  );
}
