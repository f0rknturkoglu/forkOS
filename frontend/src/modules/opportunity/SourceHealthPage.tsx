import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Badge, Button, Panel } from "@/core/ui";
import type { SourceHealth } from "@/core/types";
import { useInvalidate } from "@/lib/hooks";

type Catalog = { id: string; interval_minutes: number; kind: string };

export function SourceHealthPage() {
  const invalidate = useInvalidate();
  const { data: catalog = [] } = useQuery({ queryKey: ["source-catalog"], queryFn: () => api.get<Catalog[]>("/sources/catalog") });
  const { data: runs = [] } = useQuery({ queryKey: ["source-runs"], queryFn: () => api.get<SourceHealth[]>("/sources/runs") });
  const latest = new Map([...runs].reverse().map(run => [run.source, run]));
  const refresh = useMutation({ mutationFn: (id: string) => api.post(`/sources/${encodeURIComponent(id)}/refresh`), onSuccess: () => invalidate("source-runs", "opportunities", "notifications") });
  return <div className="space-y-4 p-6"><header><p className="text-meta text-muted">{catalog.length} kaynak · otomatik turlar dört kaynaklık dilimler halinde çalışır.</p></header><Panel><div className="divide-y divide-subtle">{catalog.map(source => { const run = latest.get(source.id); return <div key={source.id} className="flex items-center gap-3 py-2 text-meta"><div className="min-w-0 flex-1"><p className="truncate font-medium">{source.id}</p><p className="text-muted">{source.kind} · {source.interval_minutes / 60} sa · {run?.started_at ? new Date(run.started_at).toLocaleString("tr-TR") : "hiç çalışmadı"}</p>{run?.error && <p className="truncate text-danger">{run.error}</p>}</div><Badge>{run?.status ?? "new"}</Badge><span className="w-10 text-right text-muted">+{run?.items_found ?? 0}</span><Button disabled={refresh.isPending} onClick={() => refresh.mutate(source.id)}>çek</Button></div>; })}</div></Panel></div>;
}
