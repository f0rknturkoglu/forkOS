import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronDown, RefreshCw } from "lucide-react";
import { api } from "@/core/api";
import type { MediaProviderStatus } from "@/core/types";
import { Badge, Button, cx, relativeTime } from "@/core/ui";
import { useInvalidate } from "@/lib/hooks";
import { SyncProgress } from "@/modules/opportunity/SyncProgress";
import { KIND_LABELS, providerLabel } from "./shared";

type BadgeTone = "neutral" | "warn" | "ok" | "danger";

function isHealthy(provider: MediaProviderStatus): boolean {
  return provider.ready && provider.last_status !== "error";
}

function providerStatus(provider: MediaProviderStatus): { label: string; tone: BadgeTone } {
  if (provider.last_status === "error") return { label: "hata", tone: "danger" };
  if (!provider.ready) return { label: "hazır değil", tone: "warn" };
  if (provider.last_status === "empty") return { label: "boş", tone: "warn" };
  if (provider.last_status === "ok") return { label: "sağlıklı", tone: "ok" };
  return { label: "henüz çalışmadı", tone: "neutral" };
}

function latestRun(providers: MediaProviderStatus[]): string | null {
  return providers.reduce<string | null>((latest, provider) => {
    if (!provider.last_run_at || Number.isNaN(new Date(provider.last_run_at).getTime())) return latest;
    if (!latest || new Date(provider.last_run_at).getTime() > new Date(latest).getTime()) return provider.last_run_at;
    return latest;
  }, null);
}

function providerKinds(provider: MediaProviderStatus): string {
  return provider.kinds.map((kind) => KIND_LABELS[kind] ?? kind).join(" · ");
}

export function MediaSyncSummary({ online }: { online: boolean }) {
  const [open, setOpen] = useState(false);
  const wasProviderError = useRef(false);
  const invalidate = useInvalidate();
  const providers = useQuery({
    queryKey: ["media-providers"],
    queryFn: () => api.get<MediaProviderStatus[]>("/media/providers"),
  });
  const sync = useMutation({
    mutationFn: () => api.post("/media/sync"),
    onSuccess: () => invalidate("media-providers", "source-sync", "media"),
  });

  const data = providers.data ?? [];
  const healthy = data.filter(isHealthy).length;
  const lastRun = latestRun(data);
  const failed = providers.isError;

  useEffect(() => {
    if (failed && !wasProviderError.current) setOpen(true);
    wasProviderError.current = failed;
  }, [failed]);

  return (
    <details
      data-media-sync
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
      className="overflow-hidden rounded-card border border-subtle bg-surface shadow-card"
    >
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3.5 py-2.5 marker:content-none">
        <ChevronDown className={cx("shrink-0 transition-transform", open && "rotate-180")} size={15} aria-hidden="true" />
        <span className="text-body font-medium text-primary">Kaynak ayrıntıları</span>
        {providers.isLoading ? (
          <span className="ml-auto text-meta text-muted" aria-live="polite">Kaynaklar yükleniyor…</span>
        ) : failed ? (
          <span className="ml-auto text-meta text-danger">Kaynak verisi alınamadı</span>
        ) : (
          <span className="ml-auto flex flex-wrap items-center justify-end gap-2 text-meta text-muted" aria-live="polite">
            <span>{data.length} kaynak</span>
            <Badge tone={healthy === data.length && data.length > 0 ? "ok" : "warn"}>{healthy} sağlıklı</Badge>
            {lastRun && <span>son çekim {relativeTime(lastRun)}</span>}
          </span>
        )}
      </summary>

      <div className="border-t border-subtle">
        {failed ? (
          <div role="alert" className="flex flex-wrap items-center gap-3 px-3.5 py-3 text-meta text-danger">
            <span>Medya sağlayıcıları yüklenemedi: {providers.error.message}</span>
            <Button size="sm" disabled={providers.isFetching} onClick={() => { void providers.refetch(); }}>Yeniden dene</Button>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-subtle px-3.5 py-2.5">
              <p className="text-meta text-secondary">Tüm sağlayıcılar arka planda kuyruğa alınır.</p>
              <Button size="sm" disabled={!online || sync.isPending} onClick={() => sync.mutate()}>
                <RefreshCw size={13} aria-hidden="true" className={sync.isPending ? "animate-spin" : undefined} /> Şimdi tara
              </Button>
            </div>

            {sync.error && (
              <p role="alert" className="border-b border-subtle px-3.5 py-2 text-meta text-danger">
                Tarama kuyruğa alınamadı: {sync.error.message}. Lütfen tekrar deneyin.
              </p>
            )}

            {providers.isLoading ? null : data.length === 0 ? (
              <p className="px-3.5 py-3 text-meta text-muted">Yapılandırılmış medya sağlayıcısı yok.</p>
            ) : (
              <ul>
                {data.map((provider) => {
                  const status = providerStatus(provider);
                  return (
                    <li key={provider.id} className="grid gap-1 border-b border-subtle px-3.5 py-2.5 last:border-b-0 sm:grid-cols-[minmax(0,1fr)_auto] sm:gap-x-3">
                      <div className="min-w-0">
                        <p className="truncate text-body text-primary">{providerLabel(provider.id) ?? provider.id}</p>
                        <p className="truncate text-meta text-secondary">{providerKinds(provider)}</p>
                        {provider.last_error && <p className="break-words text-meta text-danger" title={`Son hata: ${provider.last_error}`}>Son hata: {provider.last_error}</p>}
                        {provider.missing_settings.map((setting) => (
                          <p key={setting} className="break-words text-meta text-warn" title={`Eksik ayar: ${setting}`}>Eksik ayar: {setting}</p>
                        ))}
                      </div>
                      <div className="flex items-start gap-2 sm:justify-end">
                        <Badge tone={status.tone}>{status.label}</Badge>
                        {provider.last_run_at && <span className="text-meta text-muted">{relativeTime(provider.last_run_at)}</span>}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
            <div className="px-3.5 py-2.5">
              <SyncProgress scope="media" compact />
            </div>
          </>
        )}
      </div>
    </details>
  );
}
