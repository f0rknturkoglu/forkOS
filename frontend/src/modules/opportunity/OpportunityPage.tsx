import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Badge, Button, Empty, Panel } from "@/core/ui";
import type { Opportunity } from "@/core/types";
import type { Todo } from "@/core/types";
import type { Document } from "@/core/types";
import { useInvalidate } from "@/lib/hooks";

const columns = ["discovered", "considering", "preparing", "applied", "interview", "accepted", "rejected"];

export function OpportunityPage() {
  const [view, setView] = useState<"board" | "table">("board");
  const [kind, setKind] = useState("");
  const [title, setTitle] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const invalidate = useInvalidate();
  const { data = [] } = useQuery({ queryKey: ["opportunities", kind], queryFn: () => api.get<Opportunity[]>(`/opportunities${qs({ kind: kind || undefined, limit: 500 })}`) });
  const groups = useMemo(() => Object.fromEntries(columns.map(c => [c, data.filter(x => x.status === c)])), [data]);
  const create = useMutation({ mutationFn: () => api.post("/opportunities", { title, kind: "job" }), onSuccess: () => { setTitle(""); invalidate("opportunities", "activity"); } });
  const patch = useMutation({ mutationFn: ({ id, status }: { id: string; status: string }) => api.patch(`/opportunities/${id}`, { status }), onSuccess: () => invalidate("opportunities", "activity") });
  return <div className="space-y-4 p-6">
    <header className="flex items-center justify-between"><div><h1 className="text-xl font-semibold">Opportunity Hub</h1><p className="text-xs text-neutral-500">İş, burs, sınav ve yüksek lisans başvuruları.</p></div><Button onClick={() => setView(view === "board" ? "table" : "board")}>{view === "board" ? "tablo" : "kanban"}</Button></header>
    <Panel title="Hızlı fırsat ekle"><div className="grid gap-2 md:grid-cols-[12rem_1fr]"><select value={kind} onChange={e => setKind(e.target.value)} className="rounded border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm"><option value="">tüm türler</option><option value="job">iş ilanları</option><option value="exam">ÖSYM / sınav</option><option value="scholarship">YLSY / burs</option><option value="msc">yüksek lisans</option></select><form className="flex gap-2" onSubmit={e => { e.preventDefault(); if (title.trim()) create.mutate(); }}><input className="flex-1 rounded border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm" value={title} onChange={e => setTitle(e.target.value)} placeholder="Fırsat başlığı"/><Button variant="primary">ekle</Button></form></div></Panel>
    {data.length === 0 ? <Empty>Henüz fırsat yok. Worker kaynakları ilk turda dolduracak.</Empty> : view === "table" ?
      <Panel><div className="divide-y divide-neutral-800">{data.map(x => <Card key={x.id} item={x} onOpen={() => setSelected(x.id)} onStatus={status => patch.mutate({ id: x.id, status })}/>)}</div></Panel> :
      <div className="grid gap-3 overflow-x-auto xl:grid-cols-4">{columns.map(column => <Panel key={column} title={`${column} · ${groups[column].length}`}><div className="space-y-2">{groups[column].map(x => <Card key={x.id} item={x} onOpen={() => setSelected(x.id)} onStatus={status => patch.mutate({ id: x.id, status })}/>)}</div></Panel>)}</div>}
    {selected && <OpportunityDetail id={selected} close={() => setSelected(null)} />}
  </div>;
}

function Card({ item, onStatus, onOpen }: { item: Opportunity; onStatus: (s: string) => void; onOpen: () => void }) {
  return <article className="rounded border border-neutral-800 bg-neutral-950/60 p-3"><div className="flex justify-between gap-2"><button onClick={onOpen} className="text-left text-sm font-medium hover:text-sky-400">{item.title}</button><Badge>p{item.priority}</Badge></div><p className="mt-1 text-xs text-neutral-500">{item.organization ?? item.source}{item.location ? ` · ${item.location}` : ""}</p>{item.deadline_at && <p className="mt-1 text-xs text-amber-400">Son: {new Date(item.deadline_at).toLocaleDateString("tr-TR")}</p>}<select className="mt-2 w-full rounded border border-neutral-800 bg-neutral-900 p-1 text-xs" value={item.status} onChange={e => onStatus(e.target.value)}>{columns.map(x => <option key={x}>{x}</option>)}</select></article>;
}

type Requirement = { id: string; name: string; status: string; required: boolean; document_entity_id: string | null };

function OpportunityDetail({ id, close }: { id: string; close: () => void }) {
  const [requirement, setRequirement] = useState(""); const [step, setStep] = useState("");
  const invalidate = useInvalidate();
  const { data: item } = useQuery({ queryKey: ["opportunity", id], queryFn: () => api.get<Opportunity>(`/opportunities/${id}`) });
  const { data: requirements = [] } = useQuery({ queryKey: ["opportunity-requirements", id], queryFn: () => api.get<Requirement[]>(`/opportunities/${id}/requirements`) });
  const { data: todos = [] } = useQuery({ queryKey: ["opportunity-todos", id], queryFn: () => api.get<Todo[]>(`/opportunities/${id}/todos`) });
  const { data: documents = [] } = useQuery({ queryKey: ["documents"], queryFn: () => api.get<Document[]>("/documents") });
  const addReq = useMutation({ mutationFn: () => api.post(`/opportunities/${id}/requirements`, { name: requirement }), onSuccess: () => { setRequirement(""); invalidate("opportunity-requirements"); } });
  const addTodo = useMutation({ mutationFn: () => api.post(`/opportunities/${id}/todos`, { title: step, priority: 3 }), onSuccess: () => { setStep(""); invalidate("opportunity-todos", "todos"); } });
  const bindDocument = useMutation({ mutationFn: ({ requirementId, documentId }: { requirementId: string; documentId: string }) => api.patch(`/requirements/${requirementId}/document`, { document_entity_id: documentId || null }), onSuccess: () => invalidate("opportunity-requirements", "activity") });
  return <div className="fixed inset-0 z-40 flex justify-end bg-black/60" onClick={close}><aside className="h-full w-full max-w-xl overflow-y-auto border-l border-neutral-800 bg-neutral-950 p-5" onClick={e => e.stopPropagation()}><div className="flex justify-between"><h2 className="text-lg font-semibold">{item?.title ?? "Yükleniyor"}</h2><Button onClick={close}>kapat</Button></div><p className="mt-2 text-sm text-neutral-500">{item?.organization} · {item?.location}</p>{item?.url && <a className="mt-2 block text-xs text-sky-400" target="_blank" href={item.url}>ilanı aç ↗</a>}<div className="mt-6 space-y-4"><Panel title="Gereksinimler"><ul className="mb-3 space-y-2 text-xs">{requirements.map(x => <li key={x.id} className="grid grid-cols-[1fr_12rem] items-center gap-2"><span>{x.document_entity_id ? "✓" : "○"} {x.name}</span><select value={x.document_entity_id ?? ""} onChange={e => bindDocument.mutate({ requirementId: x.id, documentId: e.target.value })} className="rounded border border-neutral-800 bg-neutral-900 p-1"><option value="">belge eksik</option>{documents.map(doc => <option key={doc.id} value={doc.id}>{doc.title}</option>)}</select></li>)}</ul><form className="flex gap-2" onSubmit={e => { e.preventDefault(); if (requirement.trim()) addReq.mutate(); }}><input className="flex-1 rounded border border-neutral-800 bg-neutral-900 px-2" value={requirement} onChange={e => setRequirement(e.target.value)} placeholder="CV, transkript…"/><Button>ekle</Button></form></Panel><Panel title="Başvuru adımları"><ul className="mb-3 space-y-1 text-xs">{todos.map(x => <li key={x.id}>{x.status === "done" ? "✓" : "○"} {x.title}</li>)}</ul><form className="flex gap-2" onSubmit={e => { e.preventDefault(); if (step.trim()) addTodo.mutate(); }}><input className="flex-1 rounded border border-neutral-800 bg-neutral-900 px-2" value={step} onChange={e => setStep(e.target.value)} placeholder="Cover letter hazırla"/><Button>ekle</Button></form></Panel></div></aside></div>;
}
