import { invalidateAfter } from "@/core/invalidation";
import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, ExternalLink, Trash2, Upload } from "lucide-react";
import { Markdown } from "@/core/Markdown";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { RelatedPanel } from "@/core/RelatedPanel";
import { NotesSection } from "./NotesSection";
import { useHashRoute } from "@/app/router";
import type { Document, Note } from "@/core/types";
import {
  Button,
  Chip,
  Empty,
  FileInput,
  IconButton,
  Input,
  PageFrame,
  PageHeader,
  RowList,
  Section,
  Select,
  Toolbar,
  useToast,
} from "@/core/ui";
import { useOnline } from "@/lib/hooks";

type GoogleStatus = { connected: boolean; expires_at: string | null; scopes: string | null };

/** GET /documents/usages satırı: bir belgenin fırsat kullanım listesi. */
type DocumentUsageRow = {
  document_id: string;
  usages: DocumentUsageItem[];
};

/** Tek kullanım: fırsat özeti + bağ türü (cv: başvuru CV'si, requirement: gereksinim belgesi). */
type DocumentUsageItem = {
  opportunity_id: string;
  title: string;
  status: string;
  kind: string;
  relation: "cv" | "requirement";
};

export function DocumentsPage() {
  const route = useHashRoute();
  // Kayit defteri rotasi (?focus={id}): secili belgenin iliskileri (Faz 18).
  const focusId = route.params.get("focus") ?? "";
  const [folderId, setFolderId] = useState("");
  const [category, setCategory] = useState("other");
  const toast = useToast();
  const [openingId, setOpeningId] = useState<string | null>(null);
  const online = useOnline();
  const { data: status } = useQuery({
    queryKey: ["google-status"],
    queryFn: () => api.get<GoogleStatus>("/auth/google/status"),
  });
  const { data: docs = [] } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.get<Document[]>("/documents"),
  });
  // Belge -> fırsat kullanımları artık gerçek /documents/usages ucundan gelir
  // (eskiden /opportunities?limit=2000 çekilip istemcide join kuruluyordu).
  // Query key "documents" ile BAŞLAR: belge ekle/sil/senkron sonrası
  // invalidateAfter("document.write") belge listesiyle birlikte bunu da tazeler.
  const { data: usageRows = [] } = useQuery({
    queryKey: ["documents", "usages"],
    queryFn: () => api.get<DocumentUsageRow[]>("/documents/usages"),
  });
  const docOpportunities = useMemo(() => {
    const map = new Map<string, DocumentUsageItem[]>();
    for (const row of usageRows) {
      const usages: DocumentUsageItem[] = [];
      const seen = new Set<string>();
      for (const usage of row.usages) {
        // Aynı fırsat hem cv hem requirement bağıysa tek rozet göster (eski davranış).
        if (seen.has(usage.opportunity_id)) continue;
        seen.add(usage.opportunity_id);
        usages.push(usage);
      }
      map.set(row.document_id, usages);
    }
    return map;
  }, [usageRows]);
  const sync = useMutation({
    mutationFn: () => api.post<{ synced: number }>("/documents/sync", { folder_id: folderId, category }),
    onSuccess: (result) => {
      invalidateAfter("document.write");
      toast.push(
        result.synced > 0
          ? `${result.synced} belge eşlendi`
          : "Bu klasörde doğrudan dosya bulunamadı — klasör boş olabilir ya da dosyalar alt " +
              "klasörlerde (sadece üst seviyedekiler taranır).",
        { tone: result.synced > 0 ? "ok" : "warn" },
      );
    },
    onError: (error: Error) => toast.push(`Senkron başarısız: ${error.message}`, { tone: "danger" }),
  });
  async function openDoc(doc: Document) {
    setOpeningId(doc.id);
    try {
      const { url } = await api.get<{ url: string | null }>(`/documents/${doc.id}/open`).catch(() => ({ url: null }));
      if (url) {
        window.open(url, "_blank", "noreferrer");
      } else {
        window.open(`/api/documents/${doc.id}/file`, "_blank", "noreferrer");
      }
    } catch {
      window.open(`/api/documents/${doc.id}/file`, "_blank", "noreferrer");
    } finally {
      setOpeningId(null);
    }
  }
  return (
    <PageFrame className="space-y-5">
      <PageHeader
        eyebrow="Kaynaklar"
        title="Belgeler"
        action={
          status?.connected ? (
            <Chip tone="ok">Google bağlı</Chip>
          ) : (
            <Button
              variant="primary"
              disabled={!online}
              onClick={() => {
                window.location.href = "/api/auth/google/start";
              }}
            >
              Google bağla
            </Button>
          )
        }
      />
      <p className="text-meta text-muted">
        Yerel dosyalar veya Google Drive aynası; başvurular için CV ve gereksinim belgeleri burada tutulur.
      </p>
      <UploadPanel online={online} />
      <SyncPanel
        online={online}
        connected={Boolean(status?.connected)}
        folderId={folderId}
        onFolderId={setFolderId}
        category={category}
        onCategory={setCategory}
        pending={sync.isPending}
        onSync={() => sync.mutate()}
      />
      <DocumentsList docs={docs} usageByDoc={docOpportunities} openingId={openingId} online={online} onOpen={openDoc} />

      {/* Yerel notlar (Faz 21): Drive belgelerinin yaninda, ayri modul degil. */}
      <NotesSection online={online} />

      {focusId && <DocumentFocusPanel id={focusId} online={online} />}
    </PageFrame>
  );
}

function UploadPanel({ online }: { online: boolean }) {
  const [category, setCategory] = useState("cv");
  const fileRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      form.append("category", category);
      return api.post<Document>("/documents/upload", form);
    },
    onSuccess: (doc) => {
      invalidateAfter("document.write");
      toast.push(`${doc?.title ?? "Belge"} başarıyla yüklendi`, { tone: "ok" });
      if (fileRef.current) fileRef.current.value = "";
    },
    onError: (err: Error) => toast.push(`Yükleme başarısız: ${err.message}`, { tone: "danger" }),
  });

  return (
    <Section title="Yerel Belge / CV Yükle">
      <Toolbar className="border-y-0 py-0">
        <div className="flex flex-wrap items-center gap-2">
          <FileInput
            ref={fileRef}
            accept=".pdf,.doc,.docx,.txt"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) upload.mutate(f);
            }}
          />
          <Select value={category} onChange={setCategory} className="w-36">
            <option value="cv">CV</option>
            <option value="education">Eğitim</option>
            <option value="exams">Sınavlar</option>
            <option value="certificates">Sertifikalar</option>
            <option value="other">Diğer</option>
          </Select>
          <Button variant="primary" disabled={!online || upload.isPending} onClick={() => fileRef.current?.click()}>
            <Upload size={14} /> {upload.isPending ? "Yükleniyor…" : "Dosya Seç ve Yükle"}
          </Button>
        </div>
      </Toolbar>
    </Section>
  );
}

/**
 * Secili kaydin iliskileri (Faz 18) + notsa govde gorunumu (Faz 21).
 * Not EntityTypeSpec rotasi (/documents?focus={id}) buraya gider.
 */
function DocumentFocusPanel({ id, online }: { id: string; online: boolean }) {
  const { data: note } = useQuery({
    queryKey: ["note", id],
    queryFn: () => api.get<Note>(`/notes/${id}`).catch(() => null),
    enabled: Boolean(id),
  });

  if (!note) {
    return (
      <Section title="Bağlı kayıtlar">
        <RelatedPanel entityId={id} />
      </Section>
    );
  }
  return (
    <Section title={note.title} hint={note.pinned ? "sabit" : undefined}>
      {/* Notlar markdown; [[baglanti]] ve #etiket burada da calisir. */}
      <Markdown source={note.body} links={note.resolved_links ?? []} unresolved={note.unresolved_links ?? []} />
      <div className="mt-3">
        <RelatedPanel entityId={id} relation="notes_about" title="Hakkında" />
      </div>
    </Section>
  );
}

function SyncPanel({
  online,
  connected,
  folderId,
  onFolderId,
  category,
  onCategory,
  pending,
  onSync,
}: {
  online: boolean;
  connected: boolean;
  folderId: string;
  onFolderId: (value: string) => void;
  category: string;
  onCategory: (value: string) => void;
  pending: boolean;
  onSync: () => void;
}) {
  return (
    <Section title="Drive klasörü tara">
      <Toolbar className="border-y-0 py-0">
        <form
          className="grid w-full gap-2 md:grid-cols-[1fr_12rem_auto]"
          onSubmit={(e) => {
            e.preventDefault();
            if (folderId.trim()) onSync();
          }}
        >
          <Input value={folderId} onChange={onFolderId} placeholder="Drive klasör kimliği" className="w-full" />
          <Select value={category} onChange={onCategory} className="w-full">
            <option value="cv">CV</option>
            <option value="education">Eğitim</option>
            <option value="exams">Sınavlar</option>
            <option value="certificates">Sertifikalar</option>
            <option value="other">Diğer</option>
          </Select>
          <Button type="submit" variant="primary" disabled={!online || !connected || pending}>
            Senkronla
          </Button>
        </form>
      </Toolbar>
      {!connected && (
        <p className="mt-2 text-meta text-warn">
          Google bağlı değil; uygulamanın geri kalanı normal çalışmaya devam eder.
        </p>
      )}
    </Section>
  );
}

function DocumentsList({
  docs,
  usageByDoc,
  openingId,
  online,
  onOpen,
}: {
  docs: Document[];
  usageByDoc: Map<string, DocumentUsageItem[]>;
  openingId: string | null;
  online: boolean;
  onOpen: (doc: Document) => void;
}) {
  return (
    <Section title="Belgeler" hint={`${docs.length} kayıt`}>
      {docs.length === 0 ? (
        <Empty>Henüz eşlenmiş belge yok.</Empty>
      ) : (
        <RowList>
          {docs.map((doc) => (
            <DocumentRow
              key={doc.id}
              doc={doc}
              usages={usageByDoc.get(doc.id) ?? []}
              opening={openingId === doc.id}
              online={online}
              onOpen={onOpen}
            />
          ))}
        </RowList>
      )}
    </Section>
  );
}

function DocumentRow({
  doc,
  usages,
  opening,
  online,
  onOpen,
}: {
  doc: Document;
  usages: DocumentUsageItem[];
  opening: boolean;
  online: boolean;
  onOpen: (doc: Document) => void;
}) {
  const toast = useToast();
  const del = useMutation({
    mutationFn: () => api.del(`/documents/${doc.id}`),
    onSuccess: () => {
      invalidateAfter("document.write");
      toast.push("Belge silindi", { tone: "ok" });
    },
  });

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 py-3">
      <div className="min-w-0 flex-1">
        <p className="truncate text-body text-primary">{doc.title}</p>
        <p className="truncate text-meta text-muted">
          {doc.mime} ·{" "}
          {doc.drive_modified_at ? new Date(doc.drive_modified_at).toLocaleString("tr-TR") : "güncelleme yok"}
        </p>
      </div>
      <Chip tone={doc.category === "cv" ? "accent" : "neutral"}>{doc.category ?? "other"}</Chip>
      {usages.length > 0 && (
        <span className="flex min-w-0 flex-wrap items-center gap-1">
          {usages.slice(0, 3).map((usage) => (
            <a
              key={usage.opportunity_id}
              href={`#/opportunities?focus=${usage.opportunity_id}`}
              title={`${usage.title} başvurusunda kullanılıyor — tıkla`}
              className="inline-flex min-w-0 max-w-56"
            >
              <Chip size="xs" tone="accent">
                {usage.title}
              </Chip>
            </a>
          ))}
          {usages.length > 3 && <Chip size="xs">+{usages.length - 3}</Chip>}
        </span>
      )}
      <Button size="sm" disabled={!online || opening} onClick={() => onOpen(doc)}>
        <ExternalLink size={13} /> Aç
      </Button>
      {/* Dosya indirme: yerel cache'teki orijinal dosya (FileResponse, KURAL 17
          ucu frontend'e baglandi). Offline'da indirme calismaz; hata gosterilmez. */}
      <a
        href={`/api/documents/${doc.id}/file`}
        download={doc.title}
        title="Dosyayı indir"
        className="inline-flex items-center gap-1 text-meta text-muted transition hover:text-primary"
      >
        <Download size={13} /> İndir
      </a>
      <IconButton
        tone="danger"
        disabled={!online || del.isPending}
        title="Belgeyi sil"
        onClick={async () => {
          if (
            await confirmDialog({
              title: "Belge silinsin mi?",
              body: `${doc.title} kaydı silinecek.`,
              confirmLabel: "Sil",
              tone: "danger",
            })
          ) {
            del.mutate();
          }
        }}
      >
        <Trash2 size={13} />
      </IconButton>
    </div>
  );
}
