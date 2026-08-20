import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { StudyTopic } from "@/core/types";
import { Panel } from "@/core/ui";

export function StudyWidget() {
  const { data = [] } = useQuery({ queryKey: ["study-stale"], queryFn: () => api.get<StudyTopic[]>("/study/stale?days=21") });
  return <Panel title="Tekrar bekleyen konular"><div className="space-y-1 text-xs">{data.slice(0, 5).map(t => <div key={t.id} className="flex justify-between"><span>{t.title}</span><span className="text-neutral-600">{t.last_studied_at ? new Date(t.last_studied_at).toLocaleDateString("tr-TR") : "yeni"}</span></div>)}{data.length === 0 && <span className="text-neutral-500">Bekleyen konu yok.</span>}</div></Panel>;
}
