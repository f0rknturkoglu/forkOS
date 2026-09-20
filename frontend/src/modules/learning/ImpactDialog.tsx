/**
 * Konu silme onayi: silme NELERI etkileyecegini once sayilarla gosterir.
 *
 * `GET /study/topics/{id}/impact` yazma yapmaz; yalnizca bagli kayit sayilarini
 * dondurur (alt konular dahil). Onaydan sonra konu silinir ve `onDeleted()`
 * ile cagiran yuzey secimi temizler.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Modal, SkeletonRows, useToast } from "@/core/ui";
import type { components } from "@/generated/api-schema";
import { useOnline } from "@/lib/hooks";

type TopicImpactOut = components["schemas"]["TopicImpactOut"];

/** Etki satirlari: silme sirasinda kaybolacak bagli kayitlar. */
const IMPACT_ROWS = [
  { key: "topics", label: "Konu (alt konular dahil)" },
  { key: "resources", label: "Kaynak" },
  { key: "links", label: "Bağlantı" },
  { key: "plan_slots", label: "Plan kaydı" },
  { key: "todos", label: "Görev" },
] as const;

export function ImpactDialog({
  topicId,
  topicTitle,
  open,
  onClose,
  onDeleted,
}: {
  topicId: string;
  topicTitle: string;
  open: boolean;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const online = useOnline();
  const toast = useToast();

  const {
    data: impact,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["study-topic-impact", topicId],
    enabled: open && Boolean(topicId),
    queryFn: () => api.get<TopicImpactOut>(`/study/topics/${topicId}/impact`),
  });

  const remove = useMutation({
    mutationFn: () => api.del(`/study/topics/${topicId}`),
    onSuccess: () => {
      invalidateAfter("study.write");
      toast.push(`"${topicTitle}" silindi.`, { tone: "danger" });
      onDeleted();
    },
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`"${topicTitle}" silinsin mi?`}
      hint="Bu işlem geri alınamaz."
      footer={
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>Vazgeç</Button>
          <Button variant="danger" disabled={!online || remove.isPending} onClick={() => remove.mutate()}>
            <Trash2 size={14} /> Konuyu sil
          </Button>
        </div>
      }
    >
      {isLoading ? (
        <SkeletonRows rows={3} />
      ) : error ? (
        <p role="alert" className="text-body text-danger">
          Silme etkisi alınamadı. Konu silinmedi; bağlantını kontrol edip tekrar dene.
        </p>
      ) : (
        <div className="space-y-3">
          <p className="flex items-start gap-2 text-body text-secondary">
            <AlertTriangle size={15} className="mt-0.5 shrink-0 text-warn" />
            Aşağıdaki kayıtlar bu konuyla birlikte silinir ya da bağlantısız kalır:
          </p>
          <dl className="divide-y divide-subtle rounded-card border border-subtle">
            {IMPACT_ROWS.map((row) => (
              <div key={row.key} className="flex items-center justify-between gap-3 px-3 py-2">
                <dt className="text-body text-secondary">{row.label}</dt>
                <dd className={impact?.[row.key] ? "numeral font-medium text-primary" : "numeral text-muted"}>
                  {impact?.[row.key] ?? 0}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </Modal>
  );
}
