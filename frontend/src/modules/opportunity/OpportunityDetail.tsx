import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Button, Drawer, Empty, Modal, SkeletonRows } from "@/core/ui";
import { WorkspaceInspectorContent } from "@/core/workspace/Workspace";
import type { Opportunity, OpportunityLifecycle } from "@/core/types";
import { AnnouncementDetail } from "./AnnouncementDetail";
import { JobDetail } from "./JobDetail";
import { kindLabel } from "./labels";

/**
 * Firsat detay paneli ve tam ekran çalışma alanı.
 * Hızlı panelde temel bilgiler ve X kapatma düğmesi,
 * 'Tam detayı aç' ile geniş 5 sekmeli çalışma alanı açılır.
 */
export function OpportunityDetail({
  id,
  close,
  mode = "drawer",
}: {
  id: string;
  close: () => void;
  mode?: "drawer" | "inline";
}) {
  const [fullModal, setFullModal] = useState(false);

  const itemQuery = useQuery({
    queryKey: ["opportunity", id],
    queryFn: () => api.get<Opportunity>(`/opportunities/${id}`),
  });
  const lifecycleQuery = useQuery({
    queryKey: ["opportunity-lifecycle"],
    queryFn: () => api.get<OpportunityLifecycle>("/opportunities/lifecycle"),
  });

  const item = itemQuery.data;
  const lifecycle = lifecycleQuery.data;
  const loading = itemQuery.isLoading || lifecycleQuery.isLoading;
  const failed = itemQuery.isError || lifecycleQuery.isError || (!loading && (!item || !lifecycle));

  const content = (
    <>
      {loading && <SkeletonRows rows={8} />}
      {failed && (
        <Empty variant="page" title="Kayıt bulunamadı" action={<Button onClick={close}>Kapat</Button>}>
          Fırsat yüklenemedi veya artık mevcut değil.
        </Empty>
      )}
      {!loading &&
        !failed &&
        lifecycle &&
        item &&
        (lifecycle.job_kinds.includes(item.kind) ? (
          <JobDetail item={item} onOpenFull={() => setFullModal(true)} />
        ) : (
          <AnnouncementDetail item={item} />
        ))}
    </>
  );

  return (
    <>
      {mode === "inline" ? (
        <WorkspaceInspectorContent
          title={item?.title ?? "Fırsat detayı"}
          hint={item ? kindLabel(item.kind) : undefined}
          onClose={close}
        >
          {content}
        </WorkspaceInspectorContent>
      ) : (
        <Drawer
          open
          onClose={close}
          title={item?.title ?? "Fırsat detayı"}
          hint={item ? kindLabel(item.kind) : undefined}
          ariaLabel="Fırsat detayı"
          className="sm:max-w-2xl"
        >
          {content}
        </Drawer>
      )}

      {fullModal && item && lifecycle && (
        <Modal
          open
          onClose={() => setFullModal(false)}
          title={item.title}
          hint={item.organization ?? kindLabel(item.kind)}
          className="sm:max-w-4xl"
        >
          {lifecycle.job_kinds.includes(item.kind) ? (
            <JobDetail item={item} />
          ) : (
            <AnnouncementDetail item={item} />
          )}
        </Modal>
      )}
    </>
  );
}
