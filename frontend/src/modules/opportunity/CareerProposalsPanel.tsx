import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Chip, Empty, useToast } from "@/core/ui";
import type { components } from "@/generated/api-schema";

type Proposal = components["schemas"]["ProposalOut"];

const destination: Record<Proposal["type"], string> = {
  goal: "Hedef",
  milestone: "Hedef kilometre taşı",
  learning: "Öğrenme konusu",
  project: "Mevcut proje bağı",
  todo: "Görev",
};

export function CareerProposalsPanel() {
  const toast = useToast();
  const query = useQuery({
    queryKey: ["career-proposals"],
    queryFn: () => api.get<Proposal[]>("/career/strategy/proposals"),
  });
  const refresh = useMutation({
    mutationFn: () => api.post<Proposal[]>("/career/strategy/proposals/refresh"),
    onSuccess: () => {
      invalidateAfter("career-strategy.write");
      toast.push("Öneriler güncel kanıtla hazırlandı; hiçbir kayıt otomatik oluşturulmadı.", { tone: "ok" });
    },
    onError: () => toast.push("Öneriler hazırlanamadı.", { tone: "danger" }),
  });
  const approve = useMutation({
    mutationFn: (id: string) => api.post<Proposal>(`/career/strategy/proposals/${id}/approve`),
    onSuccess: (proposal) => {
      invalidateAfter("career-strategy.write");
      toast.push(
        proposal.materialization_status === "materialized"
          ? "Öneri kanonik kayda veya mevcut projeye bağlandı."
          : "Onaylandı; hedef işlem tamamlanamadı. Karttaki uyarıyı incele.",
        { tone: proposal.materialization_status === "materialized" ? "ok" : "warn" },
      );
    },
    onError: () => {
      invalidateAfter("career-strategy.write");
      toast.push("Öneri onaylanamadı; kanıt bayatlamış olabilir. Önerileri yenile.", { tone: "danger" });
    },
  });
  const reject = useMutation({
    mutationFn: (id: string) => api.post<Proposal>(`/career/strategy/proposals/${id}/reject`),
    onSuccess: () => invalidateAfter("career-strategy.write"),
    onError: () => toast.push("Öneri reddedilemedi.", { tone: "danger" }),
  });
  const pending = query.data?.filter((item) => item.status === "proposed") ?? [];
  const decided = query.data?.filter((item) => item.status !== "proposed") ?? [];

  return (
    <div className="stack-y-3 border-t border-subtle pt-4">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="min-w-0 flex-1 text-body font-semibold text-primary">Karar bekleyen öneriler</h3>
        <Button size="sm" onClick={() => refresh.mutate()} disabled={refresh.isPending}>
          Önerileri hazırla / yenile
        </Button>
      </div>
      <p className="text-meta text-muted">
        Hazırlama yalnızca öneri kaydeder. Hedef, öğrenme veya görev ancak karttaki Onayla işleminden sonra oluşturulur.
      </p>
      {query.isError && (
        <p role="alert" className="text-meta text-danger">
          Öneriler yüklenemedi.
        </p>
      )}
      {!pending.length && <Empty title="Karar bekleyen öneri yok">Güncel kanıtlardan öneri hazırlayabilirsin.</Empty>}
      {pending.map((item) => (
        <div key={item.id} className="stack-y-2 rounded-card border border-subtle bg-surface p-3">
          <div className="flex flex-wrap items-center gap-2">
            <p className="min-w-0 flex-1 text-body font-semibold text-primary">{item.title}</p>
            <Chip tone="neutral">{destination[item.type]}</Chip>
            {item.sample_size !== null && <Chip tone="neutral">n={item.sample_size}</Chip>}
          </div>
          <p className="text-meta text-secondary">{item.rationale}</p>
          <p className="text-meta text-muted">
            Kapsam: {item.estimated_scope || "belirsiz"} · Kanıt: {item.evidence_refs.slice(0, 3).join(", ")}
          </p>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => approve.mutate(item.id)} disabled={approve.isPending || reject.isPending}>
              {item.type === "project" ? "Onayla ve bağla" : "Onayla ve oluştur"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => reject.mutate(item.id)}
              disabled={approve.isPending || reject.isPending}
            >
              Reddet
            </Button>
          </div>
        </div>
      ))}
      {decided.length > 0 && (
        <details>
          <summary className="cursor-pointer text-meta text-secondary">Geçmiş kararlar ({decided.length})</summary>
          {decided.slice(0, 10).map((item) => (
            <p key={item.id} className="mt-2 text-meta text-muted">
              {item.title} · {item.status} · {item.materialization_status}
              {item.warnings?.length ? ` · ${item.warnings.join("; ")}` : ""}
            </p>
          ))}
        </details>
      )}
    </div>
  );
}
