import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ExternalLink, Search, ShieldCheck, Upload, Users } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Chip, Empty, FileInput, Input, Section, cx, useToast } from "@/core/ui";
import type { CareerConnection, CareerConnectionsImportResult } from "@/core/types";

export function CareerConnectionsPanel({ focusId }: { focusId?: string | null }) {
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState("");
  const [lastImport, setLastImport] = useState<CareerConnectionsImportResult | null>(null);
  const { data: connections = [], isLoading } = useQuery({
    queryKey: ["career-connections", search],
    queryFn: () =>
      api.get<CareerConnection[]>(
        `/career/connections?limit=2000${search.trim() ? `&search=${encodeURIComponent(search.trim())}` : ""}`,
      ),
  });

  useEffect(() => {
    if (!focusId) return;
    document.getElementById(`career-connection-${focusId}`)?.scrollIntoView({ block: "center" });
  }, [focusId, connections.length]);

  const upload = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.post<CareerConnectionsImportResult>("/career/connections/import", form);
    },
    onSuccess: (result) => {
      setLastImport(result);
      invalidateAfter("career.write");
      toast.push(`${result.created} yeni, ${result.updated} güncellenen bağlantı`, { tone: "ok" });
      if (fileRef.current) fileRef.current.value = "";
    },
    onError: (error: Error) => toast.push(`CSV içe aktarılamadı: ${error.message}`, { tone: "danger" }),
  });

  return (
    <Section
      title="Yerel bağlantı ağı"
      hint={`${connections.length} kişi · dış ağ çağrısı yok`}
      action={
        <>
          <FileInput
            ref={fileRef}
            accept=".csv,text/csv"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) upload.mutate(file);
            }}
          />
          <Button size="sm" disabled={upload.isPending} onClick={() => fileRef.current?.click()}>
            <Upload size={13} /> {upload.isPending ? "İçe aktarılıyor…" : "Connections.csv aktar"}
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
          <ShieldCheck size={14} className="text-ok" /> CSV yalnızca bu cihazdaki PostgreSQL'e yazılır.
        </span>
      </div>

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
      ) : connections.length === 0 ? (
        <Empty title={search ? "Bu aramaya uyan bağlantı yok" : "Bağlantı ağı henüz boş"}>
          {search
            ? "Başka bir isim, kurum veya pozisyon deneyebilirsin."
            : "LinkedIn veri dışa aktarımındaki Connections.csv dosyasını seçerek warm-intro ağını kur."}
        </Empty>
      ) : (
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {connections.map((connection) => (
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
          ))}
        </div>
      )}
    </Section>
  );
}
