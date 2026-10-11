import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ExternalLink, Search, ShieldCheck, Upload, Users } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Chip, Empty, FileInput, Input, Modal, Section, cx, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { ApplicationListPage, CareerConnection, CareerConnectionsImportResult, Opportunity } from "@/core/types";
import { normalizeCompany, previewConnectionsCsv, type ConnectionPreview } from "./careerUtils";

export function CareerConnectionsPanel({ focusId }: { focusId?: string | null }) {
  const toast = useToast();
  const online = useOnline();
  const fileRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState("");
  const [lastImport, setLastImport] = useState<CareerConnectionsImportResult | null>(null);
  const [pending, setPending] = useState<{ file: File; preview: ConnectionPreview } | null>(null);
  const {
    data: connections = [],
    isLoading,
    isError: connectionsFailed,
    error: connectionsError,
    isFetching: connectionsFetching,
    refetch: refetchConnections,
  } = useQuery({
    queryKey: ["career-connections", search],
    queryFn: () =>
      api.get<CareerConnection[]>(
        `/career/connections?limit=2000${search.trim() ? `&search=${encodeURIComponent(search.trim())}` : ""}`,
      ),
  });
  const { data: applicationsPage } = useQuery({
    queryKey: ["applications"],
    queryFn: () => api.get<ApplicationListPage>("/applications?limit=200"),
  });
  const applications = applicationsPage?.items ?? [];

  /** Kurum normalizasyonu -> aynı kurumdaki ilanlar (warm-intro ipucu). */
  const jobsByCompany = useMemo(() => {
    const map = new Map<string, Opportunity[]>();
    for (const item of applications) {
      const key = normalizeCompany(item.organization);
      if (!key) continue;
      const bucket = map.get(key);
      if (bucket) bucket.push(item);
      else map.set(key, [item]);
    }
    return map;
  }, [applications]);

  useEffect(() => {
    if (!focusId) return;
    document.getElementById(`career-connection-${focusId}`)?.scrollIntoView({ block: "center" });
  }, [focusId, connections.length]);

  const upload = useMutation({
    mutationFn: (file: File) => api.upload<CareerConnectionsImportResult>("/career/connections/import", file),
    onSuccess: (result) => {
      setLastImport(result);
      setPending(null);
      invalidateAfter("career.write");
      toast.push(`${result.created} yeni, ${result.updated} güncellenen bağlantı`, { tone: "ok" });
      if (fileRef.current) fileRef.current.value = "";
    },
    onError: (error: Error) => toast.push(`CSV içe aktarılamadı: ${error.message}`, { tone: "danger" }),
  });

  async function chooseFile(file: File) {
    const text = await file.text();
    const preview = previewConnectionsCsv(text, connections);
    if (preview.total === 0) {
      toast.push("CSV'de bağlantı satırı bulunamadı; başlık satırı First Name/Last Name içermeli.", {
        tone: "warn",
      });
      if (fileRef.current) fileRef.current.value = "";
      return;
    }
    setPending({ file, preview });
  }

  return (
    <Section
      title="Yerel bağlantı ağı"
      hint={connectionsFailed ? "okunamadı" : `${connections.length} kişi · dış ağ çağrısı yok`}
      action={
        <>
          <FileInput
            ref={fileRef}
            accept=".csv,text/csv"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void chooseFile(file);
            }}
          />
          <Button
            size="sm"
            disabled={!online || upload.isPending}
            title={online ? undefined : "Çevrimdışısın: yazma kapalı"}
            onClick={() => fileRef.current?.click()}
          >
            <Upload size={13} /> {upload.isPending ? "İçe aktarılıyor…" : "Connections.csv seç"}
          </Button>
        </>
      }
    >
      <div className="mb-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
        <div className="relative">
          <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-icon" />
          <Input
            value={search}
            onChange={setSearch}
            placeholder="İsim, kurum veya pozisyon ara…"
            ariaLabel="Bağlantılarda ara"
            className="w-full pl-9"
          />
        </div>
        <span className="flex items-center gap-2 text-meta text-muted">
          <ShieldCheck size={14} className="text-ok" /> CSV yalnızca bu cihazdaki yerel PostgreSQL'e yazılır; hiçbir
          sunucuya veya dış servise gönderilmez.
        </span>
      </div>

      {!online && (
        <p role="status" className="mb-4 text-meta text-warn">
          Çevrimdışısın: CSV içe aktarılamaz, bağlantı ağı salt okunur.
        </p>
      )}

      {lastImport && (
        <div className="mb-4 flex flex-wrap gap-2 rounded-control border border-ok-border bg-ok-surface p-3">
          <Chip tone="ok">{lastImport.created} yeni</Chip>
          <Chip>{lastImport.updated} güncellendi</Chip>
          <Chip>{lastImport.skipped} değişmedi</Chip>
          <span className="text-meta text-secondary">Toplam {lastImport.total_rows} satır işlendi.</span>
        </div>
      )}

      {isLoading ? (
        <div className="h-24 animate-pulse rounded-card bg-surface-sunken" />
      ) : connectionsFailed ? (
        <div role="alert" className="stack-y-2 rounded-control border border-danger-border bg-danger-surface px-3 py-3">
          <p className="text-meta text-danger">
            Bağlantılar yüklenemedi: {connectionsError instanceof Error ? connectionsError.message : "bilinmeyen hata"}
          </p>
          <Button size="sm" disabled={connectionsFetching} onClick={() => void refetchConnections()}>
            Tekrar dene
          </Button>
        </div>
      ) : connections.length === 0 ? (
        <Empty title={search ? "Bu aramaya uyan bağlantı yok" : "Bağlantı ağı henüz boş"}>
          {search
            ? "Başka bir isim, kurum veya pozisyon deneyebilirsin."
            : "LinkedIn veri dışa aktarımındaki Connections.csv dosyasını seçerek warm-intro ağını kur."}
        </Empty>
      ) : (
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {connections.map((connection) => {
            const key = normalizeCompany(connection.company);
            const jobs = key ? (jobsByCompany.get(key) ?? []) : [];
            return (
              <article
                id={`career-connection-${connection.id}`}
                key={connection.id}
                className={cx(
                  "rounded-card border bg-surface p-3 transition",
                  focusId === connection.id ? "border-accent-border bg-accent-surface" : "border-subtle",
                )}
              >
                <div className="flex items-start gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-sunken text-muted">
                    <Users size={14} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <strong className="block truncate text-body text-primary">{connection.name}</strong>
                    <p className="mt-0.5 truncate text-meta text-secondary">
                      {[connection.position, connection.company].filter(Boolean).join(" · ") || "Bağlam belirtilmemiş"}
                    </p>
                    {key && (
                      <p
                        className="mt-1 flex items-center gap-1 text-micro text-muted"
                        title="Kurum eşleştirme anahtarı"
                      >
                        <span className="text-icon">normalize:</span> <code>{key}</code>
                      </p>
                    )}
                    {jobs.length > 0 && (
                      <p className="mt-1 text-micro text-accent">
                        Sıcak giriş: {jobs.length} ilanda aynı kurum —{" "}
                        {jobs
                          .slice(0, 2)
                          .map((job) => job.title)
                          .join(", ")}
                        {jobs.length > 2 ? "…" : ""}
                      </p>
                    )}
                    {connection.connected_on && (
                      <p className="mt-1 text-micro text-muted">
                        {new Date(`${connection.connected_on}T00:00:00`).toLocaleDateString("tr-TR")} tarihinde bağlandı
                      </p>
                    )}
                  </div>
                  {connection.profile_url && (
                    <a
                      href={connection.profile_url}
                      target="_blank"
                      rel="noreferrer"
                      title={`${connection.name} profilini aç`}
                      aria-label={`${connection.name} profilini aç`}
                      className="text-muted transition hover:text-primary"
                    >
                      <ExternalLink size={14} />
                    </a>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      <Modal
        open={pending !== null}
        onClose={() => {
          setPending(null);
          if (fileRef.current) fileRef.current.value = "";
        }}
        title="İçe aktarma önizlemesi"
        hint="Yazmadan önce dosya yalnızca bu cihazda okunur."
        footer={
          <div className="flex justify-end gap-2">
            <Button
              onClick={() => {
                setPending(null);
                if (fileRef.current) fileRef.current.value = "";
              }}
            >
              Vazgeç
            </Button>
            <Button
              variant="primary"
              disabled={!online || upload.isPending}
              title={online ? undefined : "Çevrimdışısın: yazma kapalı"}
              onClick={() => pending && upload.mutate(pending.file)}
            >
              <Upload size={13} /> {upload.isPending ? "İçe aktarılıyor…" : "İçe aktar"}
            </Button>
          </div>
        }
      >
        {pending && (
          <div className="stack-y-3">
            <div className="flex flex-wrap gap-2">
              <Chip tone="accent">{pending.preview.total} satır</Chip>
              <Chip tone={pending.preview.duplicates > 0 ? "warn" : "ok"}>{pending.preview.duplicates} tekrar</Chip>
              <Chip>{pending.preview.total - pending.preview.duplicates} yeni</Chip>
            </div>
            <p className="text-meta text-secondary">
              Tekrarlar mevcut ağdaki profil/e-posta/kurum kimliğine göre işaretlendi; içe aktarımda güncellenir, kopya
              oluşmaz.
            </p>
            <p className="flex items-center gap-2 rounded-control border border-ok-border bg-ok-surface p-2 text-meta text-secondary">
              <ShieldCheck size={14} className="text-ok" /> Bu CSV yalnızca bu cihazdaki yerel PostgreSQL'e yazılır;
              makineden dışarı çıkmaz.
            </p>
            <div className="max-h-56 stack-y-1 overflow-y-auto">
              {pending.preview.rows.slice(0, 50).map((row, index) => (
                <div
                  key={`${row.identity}-${index}`}
                  className="flex items-center justify-between gap-2 rounded-control border border-subtle px-2 py-1 text-meta"
                >
                  <span className="min-w-0 truncate text-secondary">
                    {[row.first_name, row.last_name].filter(Boolean).join(" ") || row.email || row.profile_url}
                    {row.company ? ` · ${row.company}` : ""}
                  </span>
                  {row.duplicate ? <Chip tone="warn">tekrar</Chip> : <Chip tone="ok">yeni</Chip>}
                </div>
              ))}
            </div>
          </div>
        )}
      </Modal>
    </Section>
  );
}
