import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import type { PomodoroSession } from "@/core/types";
import { Button, Checkbox, Modal, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";

/** Olcu -> kullanici dili; "+1 sayfa" gibi etiketler icin. */
const MEASURE_LABELS: Record<string, string> = {
  page: "sayfa",
  episode: "bölüm",
  chapter: "bölüm",
  track: "parça",
  minute: "dakika",
  hour: "saat",
  item: "kayıt",
};

interface DetailItem {
  progress_measure: string | null;
  kind: string;
  title: string;
}

/**
 * Seans sonu: odak suresi medyaya aktarilsin mi?
 *
 * Iki secenek sunar -- yalniz sure (`action="session"`, ilerleme DEGISMEZ) ya da
 * sure + 1 birim ilerleme (`action="quick"`). Iki durumda da `client_uuid`
 * seans id'sinden turetilir: ayni seans iki kez yazilamaz (backend
 * `media_consumption.client_uuid` UNIQUE + replay karsilastirmasi).
 */
export function MediaSessionTransfer({ session, onClose }: { session: PomodoroSession | null; onClose: () => void }) {
  const online = useOnline();
  const toast = useToast();
  const [alsoProgress, setAlsoProgress] = useState(false);
  const itemId = session?.context_entity_id ?? "";

  const detail = useQuery({
    queryKey: ["media-detail", itemId, "session-transfer"],
    queryFn: () => api.get<{ item: DetailItem }>(`/media/${encodeURIComponent(itemId)}`),
    enabled: Boolean(session && itemId),
  });

  const minutes = Math.max(1, Math.round(session?.actual_min ?? session?.planned_min ?? 0));
  const measure = detail.data?.item.progress_measure ?? null;
  const unitLabel = measureLabel(measure);

  const transfer = useMutation({
    mutationFn: () =>
      api.post(`/media/${encodeURIComponent(itemId)}/consumptions`, {
        // Ayni seans iki kez aktarilamaz: idempotency anahtari seans id'sinin
        // KENDISI (client_uuid uuid tipinde; onek kabul edilmez).
        client_uuid: session?.id,
        action: alsoProgress ? "quick" : "session",
        ...(alsoProgress ? { amount: 1 } : {}),
        ...(measure ? { measure } : {}),
        duration_min: minutes,
        meta: { pomodoro_session_id: session?.id },
      }),
    onSuccess: () => {
      invalidateAfter("media.write");
      toast.push(alsoProgress ? `${minutes} dk ve +1 ${unitLabel} kaydedildi.` : `${minutes} dk medyaya işlendi.`, {
        tone: "ok",
      });
      setAlsoProgress(false);
      onClose();
    },
    onError: (error: Error) => toast.push(error.message, { tone: "danger" }),
  });

  return (
    <Modal
      open={Boolean(session)}
      onClose={onClose}
      title="Seansı medyaya işle"
      hint={session ? `${session.context_title ?? "Medya"} · ${minutes} dk odak` : undefined}
      footer={
        <div className="flex flex-wrap justify-end gap-2">
          <Button disabled={transfer.isPending} onClick={onClose}>
            Yalnızca odak süresini kaydet
          </Button>
          <Button
            variant="primary"
            disabled={!online || transfer.isPending || !itemId}
            onClick={() => transfer.mutate()}
          >
            {alsoProgress ? `Süreyi ve +1 ${unitLabel} kaydet` : "Süreyi tüketime aktar"}
          </Button>
        </div>
      }
    >
      <div className="space-y-3">
        <p className="text-meta text-secondary">
          Odak süresi medya kaydının tüketim geçmişine eklenir. İlerleme yalnızca sen istersen artar.
        </p>
        <Checkbox
          checked={alsoProgress}
          onChange={setAlsoProgress}
          disabled={!online || transfer.isPending}
          label={`İlerlemeyi de +1 ${unitLabel} artır`}
        />
        {!online && (
          <p role="status" className="text-meta text-muted">
            Çevrimdışıyken tüketim kaydedilemez; süre yalnızca Pomodoro geçmişinde kalır.
          </p>
        )}
      </div>
    </Modal>
  );
}

/** Seans aktariminda kullanilan olcu etiketi; backend `MEASURES` ile ayni. */
export function measureLabel(measure: string | null): string {
  if (!measure) return "kayıt";
  return MEASURE_LABELS[measure] ?? measure;
}
