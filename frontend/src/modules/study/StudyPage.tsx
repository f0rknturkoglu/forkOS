import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import type { StudyArea, StudyTopic } from "@/core/types";
import { Badge, Button, Empty, Panel } from "@/core/ui";
import { useInvalidate } from "@/lib/hooks";

type TopicStats = { minutes: number; sessions: number };

export function StudyPage() {
  const [areaId, setAreaId] = useState(""); const [areaTitle, setAreaTitle] = useState("");
  const [topicTitle, setTopicTitle] = useState(""); const [selected, setSelected] = useState<StudyTopic | null>(null);
  const invalidate = useInvalidate();
  const { data: areas = [] } = useQuery({ queryKey: ["study-areas"], queryFn: () => api.get<StudyArea[]>("/study/areas") });
  useEffect(() => { if (!areaId && areas[0]) setAreaId(areas[0].id); }, [areas, areaId]);
  const { data: topics = [] } = useQuery({ queryKey: ["study-topics", areaId], enabled: Boolean(areaId), queryFn: () => api.get<StudyTopic[]>(`/study/topics?area_id=${areaId}`) });
  const { data: stats } = useQuery({ queryKey: ["study-topic-stats", selected?.id], enabled: Boolean(selected), queryFn: () => api.get<TopicStats>(`/study/topics/${selected?.id}/stats`) });
  const addArea = useMutation({ mutationFn: () => api.post("/study/areas", { title: areaTitle }), onSuccess: () => { setAreaTitle(""); invalidate("study-areas"); } });
  const addTopic = useMutation({ mutationFn: () => api.post("/study/topics", { title: topicTitle, area_id: areaId }), onSuccess: () => { setTopicTitle(""); invalidate("study-topics"); } });
  const patch = useMutation({ mutationFn: (body: Record<string, unknown>) => api.patch(`/study/topics/${selected?.id}`, body), onSuccess: () => invalidate("study-topics", "study-topic-stats") });
  return <div className="space-y-4 p-6"><header><h1 className="text-xl font-semibold">Study Map</h1><p className="text-xs text-neutral-500">Alan → konu ağacı; odak süreleri Pomodoro’dan türetilir.</p></header>
    <div className="grid gap-4 lg:grid-cols-[15rem_1fr_18rem]"><Panel title="Alanlar"><div className="space-y-2">{areas.map(a => <button key={a.id} onClick={() => { setAreaId(a.id); setSelected(null); }} className={`block w-full rounded border px-3 py-2 text-left text-sm ${areaId === a.id ? "border-sky-700 bg-sky-950/40" : "border-neutral-800"}`}>{a.title}</button>)}</div><form className="mt-3 flex gap-2" onSubmit={e => { e.preventDefault(); if (areaTitle.trim()) addArea.mutate(); }}><input value={areaTitle} onChange={e => setAreaTitle(e.target.value)} className="min-w-0 flex-1 rounded border border-neutral-800 bg-neutral-950 px-2 text-xs" placeholder="Yeni alan"/><Button type="submit">+</Button></form></Panel>
      <Panel title="Konu ağacı">{topics.length ? <TopicTree items={topics} select={setSelected}/> : <Empty>Konu yok.</Empty>}<form className="mt-4 flex gap-2" onSubmit={e => { e.preventDefault(); if (topicTitle.trim() && areaId) addTopic.mutate(); }}><input value={topicTitle} onChange={e => setTopicTitle(e.target.value)} className="flex-1 rounded border border-neutral-800 bg-neutral-950 px-2 py-1 text-xs" placeholder="Yeni kök konu"/><Button type="submit">ekle</Button></form></Panel>
      <Panel title="Konu detayı">{selected ? <div className="space-y-4"><div><h2 className="font-medium">{selected.title}</h2><p className="text-xs text-neutral-500">{stats?.minutes ?? 0} dk · {stats?.sessions ?? 0} session</p></div><label className="block text-xs text-neutral-500">Durum<select value={selected.status} onChange={e => patch.mutate({ status: e.target.value })} className="mt-1 w-full rounded border border-neutral-800 bg-neutral-950 p-2"><option value="not_started">başlamadı</option><option value="in_progress">devam</option><option value="done">tamam</option></select></label><div><p className="mb-1 text-xs text-neutral-500">Güven</p><div className="flex gap-1">{[1,2,3,4,5].map(n => <Button key={n} variant={selected.confidence === n ? "primary" : "ghost"} onClick={() => patch.mutate({ confidence: n })}>{n}</Button>)}</div></div><Button variant="primary" onClick={() => navigate(`/pomodoro?context=${selected.id}&title=${encodeURIComponent(selected.title)}`)}>Pomodoro başlat</Button></div> : <Empty>Bir konu seç.</Empty>}</Panel></div></div>;
}

function TopicTree({ items, select, depth = 0 }: { items: StudyTopic[]; select: (t: StudyTopic) => void; depth?: number }) {
  return <div>{items.map(t => <div key={t.id}><button onClick={() => select(t)} style={{ paddingLeft: `${depth * 16 + 8}px` }} className="flex w-full items-center justify-between rounded py-2 pr-2 text-left text-sm hover:bg-neutral-800"><span>{t.title}</span><Badge tone={t.status === "done" ? "ok" : "neutral"}>{t.confidence ? `${t.confidence}/5` : t.status}</Badge></button><TopicTree items={t.children ?? []} select={select} depth={depth + 1}/></div>)}</div>;
}
