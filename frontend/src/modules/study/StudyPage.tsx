import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import type { StudyArea, StudyTopic } from "@/core/types";
import { Badge, Button, Empty, IconButton, PageFrame, PageHeader, Section, cx } from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { useInvalidate, useOnline } from "@/lib/hooks";

type TopicStats = { minutes: number; sessions: number };

export function StudyPage() {
  const [areaId, setAreaId] = useState(""); const [areaTitle, setAreaTitle] = useState("");
  const [topicTitle, setTopicTitle] = useState(""); const [selected, setSelected] = useState<StudyTopic | null>(null);
  const invalidate = useInvalidate();
  const online = useOnline();
  const { data: areas = [] } = useQuery({ queryKey: ["study-areas"], queryFn: () => api.get<StudyArea[]>("/study/areas") });
  useEffect(() => { if (!areaId && areas[0]) setAreaId(areas[0].id); }, [areas, areaId]);
  const { data: topics = [] } = useQuery({ queryKey: ["study-topics", areaId], enabled: Boolean(areaId), queryFn: () => api.get<StudyTopic[]>(`/study/topics?area_id=${areaId}`) });
  const { data: stats } = useQuery({ queryKey: ["study-topic-stats", selected?.id], enabled: Boolean(selected), queryFn: () => api.get<TopicStats>(`/study/topics/${selected?.id}/stats`) });
  const addArea = useMutation({ mutationFn: () => api.post("/study/areas", { title: areaTitle }), onSuccess: () => { setAreaTitle(""); invalidate("study-areas"); } });
  const addTopic = useMutation({ mutationFn: () => api.post("/study/topics", { title: topicTitle, area_id: areaId }), onSuccess: () => { setTopicTitle(""); invalidate("study-topics", "activity"); } });
  const removeTopic = useMutation({ mutationFn: (id: string) => api.del(`/study/topics/${id}`),
    onSuccess: () => { setSelected(null); invalidate("study-topics", "study-areas", "activity"); } });
  const patch = useMutation({ mutationFn: (body: Record<string, unknown>) => api.patch(`/study/topics/${selected?.id}`, body), onSuccess: () => invalidate("study-topics", "study-topic-stats", "activity", "review-preview") });
  return <PageFrame className="space-y-5"><PageHeader eyebrow="Takip" title="Çalışma" /><p className="text-meta text-muted">Alan → konu ağacı; odak süreleri Pomodoro’dan türetilir.</p>
    <div className="grid min-w-0 divide-y divide-subtle border-y border-subtle lg:grid-cols-[15rem_minmax(0,1fr)_18rem] lg:divide-x lg:divide-y-0"><Section title="Alanlar" className="min-w-0 py-3 lg:pr-4"><div className="divide-y divide-subtle border-y border-subtle">{areas.map(a => <button key={a.id} onClick={() => { setAreaId(a.id); setSelected(null); }} className={cx("block w-full px-2 py-2 text-left text-body hover:bg-surface-hover", areaId === a.id && "bg-accent-surface text-primary")}>{a.title}</button>)}</div><form className="mt-3 flex gap-2" onSubmit={e => { e.preventDefault(); if (areaTitle.trim()) addArea.mutate(); }}><input value={areaTitle} onChange={e => setAreaTitle(e.target.value)} className="min-w-0 flex-1 rounded border border-subtle bg-canvas px-2 text-meta" placeholder="Yeni alan"/><Button type="submit" disabled={!online || addArea.isPending}>+</Button></form></Section>
      <Section title="Konu ağacı" className="min-w-0 py-3 lg:px-4">{topics.length ? <TopicTree items={topics} select={setSelected}/> : <Empty>Konu yok.</Empty>}<form className="mt-4 flex gap-2" onSubmit={e => { e.preventDefault(); if (topicTitle.trim() && areaId) addTopic.mutate(); }}><input value={topicTitle} onChange={e => setTopicTitle(e.target.value)} className="min-w-0 flex-1 rounded border border-subtle bg-canvas px-2 py-1 text-meta" placeholder="Yeni kök konu"/><Button type="submit" disabled={!online || addTopic.isPending}>Ekle</Button></form></Section>
      <Section title="Konu ayrıntısı" className="min-w-0 py-3 lg:pl-4">{selected ? <div className="space-y-4"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><h2 className="font-medium">{selected.title}</h2><p className="text-meta text-muted">{stats?.minutes ?? 0} dk · {stats?.sessions ?? 0} seans</p></div><IconButton title="Konuyu sil" tone="danger" disabled={!online} onClick={async () => { const ok = await confirmDialog({ title: `"${selected.title}" silinsin mi?`, body: "Alt konuları da gider.", confirmLabel: "Sil", tone: "danger" }); if (ok) removeTopic.mutate(selected.id); }}><Trash2 size={14}/></IconButton></div><label className="block text-meta text-muted">Durum<select value={selected.status} disabled={!online} onChange={e => patch.mutate({ status: e.target.value })} className="mt-1 w-full rounded border border-subtle bg-canvas p-2"><option value="not_started">başlamadı</option><option value="in_progress">devam</option><option value="done">tamam</option></select></label><div><p className="mb-1 text-meta text-muted">Güven</p><div className="flex gap-1">{[1,2,3,4,5].map(n => <Button key={n} disabled={!online} variant={selected.confidence === n ? "primary" : "ghost"} onClick={() => patch.mutate({ confidence: n })}>{n}</Button>)}</div></div><Button variant="primary" onClick={() => navigate(`/pomodoro?context=${selected.id}&title=${encodeURIComponent(selected.title)}`)}>Pomodoro başlat</Button></div> : <Empty>Bir konu seç.</Empty>}</Section></div></PageFrame>;
}

function TopicTree({ items, select, depth = 0 }: { items: StudyTopic[]; select: (t: StudyTopic) => void; depth?: number }) {
  return <div>{items.map(t => <div key={t.id}><button onClick={() => select(t)} style={{ paddingLeft: `${depth * 16 + 8}px` }} className="flex w-full items-center justify-between rounded py-2 pr-2 text-left text-body hover:bg-surface-hover"><span>{t.title}</span><Badge tone={t.status === "done" ? "ok" : "neutral"}>{t.confidence ? `${t.confidence}/5` : t.status}</Badge></button><TopicTree items={t.children ?? []} select={select} depth={depth + 1}/></div>)}</div>;
}
