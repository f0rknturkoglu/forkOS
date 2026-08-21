import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { Document } from "@/core/types";
import { Badge, Button, Empty, Panel } from "@/core/ui";
import { useInvalidate } from "@/lib/hooks";

type GoogleStatus = { connected: boolean; expires_at: string | null; scopes: string | null };
export function DocumentsPage() {
  const [folderId, setFolderId] = useState(""); const [category, setCategory] = useState("other"); const invalidate = useInvalidate();
  const { data: status } = useQuery({ queryKey: ["google-status"], queryFn: () => api.get<GoogleStatus>("/auth/google/status") });
  const { data: docs = [] } = useQuery({ queryKey: ["documents"], queryFn: () => api.get<Document[]>("/documents") });
  const sync = useMutation({ mutationFn: () => api.post<{ synced: number }>("/documents/sync", { folder_id: folderId, category }), onSuccess: () => invalidate("documents", "activity") });
  return <div className="space-y-4 p-6"><header className="flex items-center justify-between"><div><p className="text-meta text-muted">Drive dosyalarının yalnızca metadata aynası; dosya içeriği yerelde tutulmaz.</p></div>{status?.connected ? <Badge tone="ok">Google bağlı</Badge> : <Button variant="primary" onClick={() => { window.location.href = "/api/auth/google/start"; }}>Google bağla</Button>}</header>
    <Panel title="Drive klasörü tara"><form className="grid gap-2 md:grid-cols-[1fr_12rem_auto]" onSubmit={e => { e.preventDefault(); if (folderId.trim()) sync.mutate(); }}><input value={folderId} onChange={e => setFolderId(e.target.value)} placeholder="Drive folder ID" className="rounded border border-subtle bg-canvas px-3 py-2 text-body"/><select value={category} onChange={e => setCategory(e.target.value)} className="rounded border border-subtle bg-canvas px-3 py-2 text-body"><option value="cv">CV</option><option value="education">Education</option><option value="exams">Exams</option><option value="certificates">Certificates</option><option value="other">Other</option></select><Button type="submit" variant="primary" disabled={!status?.connected || sync.isPending}>senkronla</Button></form>{!status?.connected && <p className="mt-2 text-meta text-warn">Google bağlı değil; uygulamanın geri kalanı normal çalışmaya devam eder.</p>}</Panel>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{docs.map(doc => <Panel key={doc.id} title={doc.title} action={<Badge>{doc.category ?? "other"}</Badge>}><p className="truncate text-meta text-muted">{doc.mime}</p><p className="mt-1 text-meta text-muted">Drive güncelleme: {doc.drive_modified_at ? new Date(doc.drive_modified_at).toLocaleString("tr-TR") : "—"}</p>{doc.web_view_link && <a target="_blank" href={doc.web_view_link} className="mt-3 inline-block text-meta text-accent">Drive’da aç ↗</a>}</Panel>)}</div>{docs.length === 0 && <Empty>Henüz eşlenmiş belge yok.</Empty>}</div>;
}
