import { invalidateAfter } from "@/core/invalidation";
import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { api, qs } from "@/core/api";
import type { Document, Opportunity } from "@/core/types";
import {Button, Chip, Empty, Input, PageFrame, PageHeader, RowList, Section, Select, Toolbar, useToast} from "@/core/ui";
import {useOnline} from "@/lib/hooks";

type GoogleStatus = { connected: boolean; expires_at: string | null; scopes: string | null };
export function DocumentsPage() {
  const [folderId, setFolderId] = useState(""); const [category, setCategory] = useState("other"); const toast = useToast();
  const [openingId, setOpeningId] = useState<string | null>(null);
  const online = useOnline();
  const { data: status } = useQuery({ queryKey: ["google-status"], queryFn: () => api.get<GoogleStatus>("/auth/google/status") });
  const { data: docs = [] } = useQuery({ queryKey: ["documents"], queryFn: () => api.get<Document[]>("/documents") });
  // Fırsat sayfasıyla aynı cache anahtarı: belge hangi başvurularda kullanılıyor
  // sorusunu listeyi istemcide filtreleyerek yanıtlarız (backend'de belgeye göre
  // fırsat filtreleyen ayrı bir uç yok; cv/requirement bağları listede gelir).
  const { data: opportunities = [] } = useQuery({
    queryKey: ["opportunities"],
    queryFn: () => api.get<Opportunity[]>(`/opportunities${qs({ limit: 2000 })}`),
  });
  const docOpportunities = useMemo(() => {
    const map = new Map<string, Opportunity[]>();
    for (const opp of opportunities) {
      const seen = new Set<string>();
      for (const docId of [opp.cv_document_id, opp.requirement_document_id]) {
        if (!docId || seen.has(docId)) continue;
        seen.add(docId);
        map.set(docId, [...(map.get(docId) ?? []), opp]);
      }
    }
    return map;
  }, [opportunities]);
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
  async function openDoc(doc: Document) {
    setOpeningId(doc.id);
    try {
      const { url } = await api.get<{ url: string | null }>(`/documents/${doc.id}/open`);
      if (!url) {
        toast.push("Bu belge için Drive bağlantısı yok", { tone: "warn" });
        return;
      }
      window.open(url, "_blank", "noreferrer");
    } catch (error: unknown) {
      toast.push(`Belge açılamadı: ${error instanceof Error ? error.message : String(error)}`, { tone: "danger" });
    } finally {
      setOpeningId(null);
    }
  }
  return <PageFrame className="space-y-5"><PageHeader eyebrow="Kaynaklar" title="Belgeler" action={status?.connected ? <Chip tone="ok">Google bağlı</Chip> : <Button variant="primary" disabled={!online} onClick={() => { window.location.href = "/api/auth/google/start"; }}>Google bağla</Button>} />
    <p className="text-meta text-muted">Drive dosyalarının yalnızca metadata aynası; dosya içeriği yerelde tutulmaz.</p>
    <Section title="Drive klasörü tara"><Toolbar className="border-y-0 py-0"><form className="grid w-full gap-2 md:grid-cols-[1fr_12rem_auto]" onSubmit={e => { e.preventDefault(); if (folderId.trim()) sync.mutate(); }}><Input value={folderId} onChange={setFolderId} placeholder="Drive klasör kimliği" className="w-full"/><Select value={category} onChange={setCategory} className="w-full"><option value="cv">CV</option><option value="education">Eğitim</option><option value="exams">Sınavlar</option><option value="certificates">Sertifikalar</option><option value="other">Diğer</option></Select><Button type="submit" variant="primary" disabled={!online || !status?.connected || sync.isPending}>Senkronla</Button></form></Toolbar>{!status?.connected && <p className="mt-2 text-meta text-warn">Google bağlı değil; uygulamanın geri kalanı normal çalışmaya devam eder.</p>}</Section>
    <Section title="Belgeler" hint={`${docs.length} kayıt`}>{docs.length === 0 ? <Empty>Henüz eşlenmiş belge yok.</Empty> : <RowList>{docs.map(doc => {
      const usage = docOpportunities.get(doc.id) ?? [];
      return <div key={doc.id} className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 py-3"><div className="min-w-0 flex-1"><p className="truncate text-body text-primary">{doc.title}</p><p className="truncate text-meta text-muted">{doc.mime} · {doc.drive_modified_at ? new Date(doc.drive_modified_at).toLocaleString("tr-TR") : "güncelleme yok"}</p></div><Chip>{doc.category ?? "other"}</Chip>{usage.length > 0 && <span className="flex min-w-0 flex-wrap items-center gap-1">{usage.slice(0, 3).map(opp => <a key={opp.id} href={`#/opportunities?focus=${opp.id}`} title={`${opp.title} başvurusunda kullanılıyor — tıkla`} className="inline-flex min-w-0 max-w-56"><Chip size="xs" tone="accent">{opp.title}</Chip></a>)}{usage.length > 3 && <Chip size="xs">+{usage.length - 3}</Chip>}</span>}<Button size="sm" disabled={!online || openingId === doc.id} onClick={() => openDoc(doc)}><ExternalLink size={13} /> Aç</Button></div>;
    })}</RowList>}</Section></PageFrame>;
}
