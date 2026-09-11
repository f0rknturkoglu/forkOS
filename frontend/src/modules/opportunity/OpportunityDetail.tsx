import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Button, Drawer, Empty, SkeletonRows } from "@/core/ui";
import type { Opportunity, OpportunityLifecycle } from "@/core/types";
import { AnnouncementDetail } from "./AnnouncementDetail";
import { JobDetail } from "./JobDetail";
import { kindLabel } from "./labels";

/**
 * Firsat detay cekmecesi. Iki ayri calisma yuzeyine dagitir:
 * is ilanlari -> `JobDetail`, duyurular -> `AnnouncementDetail`.
 *
 * Tur karari elle kopyalanmis bir listeden DEGIL, backend'in
 * `GET /opportunities/lifecycle` cevabindaki `job_kinds` kumesinden gelir.
 * Cekmece odak tuzagi, Escape ve odak iadesini `Drawer` primitifi tasir.
 */
export function OpportunityDetail({ id, close }: { id: string; close: () => void }) {
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

  return (
    <Drawer
      open
      onClose={close}
      title={item?.title ?? "Fırsat detayı"}
      hint={item ? kindLabel(item.kind) : undefined}
      ariaLabel="Fırsat detayı"
      className="sm:max-w-2xl"
    >
      {loading && <SkeletonRows rows={8} />}
      {failed && (
        <Empty
          variant="page"
          title="Kayıt bulunamadı"
          action={
            <Button variant="secondary" onClick={close}>
              Kapat
            </Button>
          }
        >
          Fırsat yüklenemedi veya artık mevcut değil.
        </Empty>
      )}
      {!loading &&
        !failed &&
        lifecycle &&
        item &&
        (lifecycle.job_kinds.includes(item.kind) ? <JobDetail item={item} /> : <AnnouncementDetail item={item} />)}
    </Drawer>
  );
}
