import { invalidateAfter } from "@/core/invalidation";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { Document } from "@/core/types";
import {Button, Chip, Empty, Input, PageFrame, PageHeader, RowList, Section, Select, Surface, Toolbar, useToast} from "@/core/ui";
import {useOnline} from "@/lib/hooks";

type GoogleStatus = { connected: boolean; expires_at: string | null; scopes: string | null };
export function DocumentsPage() {
  const [folderId, setFolderId] = useState(""); const [category, setCategory] = useState("other"); const toast = useToast();
  const online = useOnline();
  const { data: status } = useQuery({ queryKey: ["google-status"], queryFn: () => api.get<GoogleStatus>("/auth/google/status") });
  const { data: docs = [] } = useQuery({ queryKey: ["documents"], queryFn: () => api.get<Document[]>("/documents") });
  const sync = useMutation({
    mutationFn: () => api.post<{ synced: number }>("/documents/sync", { folder_id: folderId, category }),
    onSuccess: (result) => {
      invalidateAfter("document.write");
      toast.push(
        result.synced > 0
          ? `${result.synced} belge eşlendi`
          : "Bu klasörde doğrudan dosya bulunamadı — klasör boş olabilir ya da dosyalar alt klasörlerde (sadece üst seviyedekiler taranır).",
        { tone: result.synced > 0 ? "ok" : "warn" },
      );
    },
    onError: (error: Error) => toast.push(`Senkron başarısız: ${error.message}`, { tone: "danger" }),
  });
  return <PageFrame className="space-y-5"><PageHeader eyebrow="Kaynaklar" title="Belgeler" action={status?.connected ? <Chip tone="ok">Google bağlı</Chip> : <Button variant="primary" disabled={!online} onClick={() => { window.location.href = "/api/auth/google/start"; }}>Google bağla</Button>} />
    <p className="text-meta text-muted">Drive dosyalarının yalnızca metadata aynası; dosya içeriği yerelde tutulmaz.</p>
    <Section title="Drive klasörü tara"><Toolbar className="border-y-0 py-0"><form className="grid w-full gap-2 md:grid-cols-[1fr_12rem_auto]" onSubmit={e => { e.preventDefault(); if (folderId.trim()) sync.mutate(); }}><Input value={folderId} onChange={setFolderId} placeholder="Drive klasör kimliği" className="w-full"/><Select value={category} onChange={setCategory} className="w-full"><option value="cv">CV</option><option value="education">Eğitim</option><option value="exams">Sınavlar</option><option value="certificates">Sertifikalar</option><option value="other">Diğer</option></Select><Button type="submit" variant="primary" disabled={!online || !status?.connected || sync.isPending}>Senkronla</Button></form></Toolbar>{!status?.connected && <p className="mt-2 text-meta text-warn">Google bağlı değil; uygulamanın geri kalanı normal çalışmaya devam eder.</p>}</Section>
    <Section title="Belgeler" hint={`${docs.length} kayıt`}>{docs.length === 0 ? <Empty>Henüz eşlenmiş belge yok.</Empty> : <RowList>{docs.map(doc => <div key={doc.id} className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 py-3"><div className="min-w-0 flex-1"><p className="truncate text-body text-primary">{doc.title}</p><p className="truncate text-meta text-muted">{doc.mime} · {doc.drive_modified_at ? new Date(doc.drive_modified_at).toLocaleString("tr-TR") : "güncelleme yok"}</p></div><Chip>{doc.category ?? "other"}</Chip>{doc.web_view_link && <a target="_blank" rel="noreferrer" href={doc.web_view_link} className="text-meta text-accent">Drive’da aç ↗</a>}</div>)}</RowList>}</Section></PageFrame>;
}
