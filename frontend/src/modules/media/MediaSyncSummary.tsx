import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronDown, RefreshCw } from "lucide-react";
import { api } from "@/core/api";
import type { MediaProviderStatus } from "@/core/types";
import { Button, Empty, cx, relativeTime } from "@/core/ui";
import { SyncProgress } from "@/core/SyncProgress";
import { KIND_LABELS, providerLabel } from "./shared";

/** Ham ayar anahtari kullaniciya gosterilmez; insan dili karsiligi yazilir. */
const SETTING_LABELS: Record<string, string> = {
  "media.tmdb_key": "TMDB anahtarı",
  "media.igdb_client_id": "IGDB kimlik bilgileri",
  "media.igdb_client_secret": "IGDB kimlik bilgileri",
  "media.google_books_key": "Google Books anahtarı",
};

/** Ozet satirinda durum kirilimi; ayni sirada yazilir. */
const STATE_SUMMARY: Record<string, string> = {
  never_run: "henüz çalışmadı",
  running: "taranıyor",
  ok: "son tarama başarılı",
  empty: "son tarama boş",
  error: "son tarama hatalı",
};

const STATUS_TONE: Record<string, string> = {
  ok: "text-ok",
  warn: "text-warn",
  danger: "text-danger",
  neutral: "text-muted",
};

function missingSettingsText(settings: string[]): string {
  const labels = [...new Set(settings.map((setting) => SETTING_LABELS[setting] ?? setting))];
  return labels.join(", ");
}

/** Satir durumu: `provider.state` tek kaynaktir (last_status'a geri dusulmez). */
function providerStatus(provider: MediaProviderStatus): { label: string; tone: string } {
  switch (provider.state) {
    case "missing_settings":
      return { label: `Eksik yapılandırma: ${missingSettingsText(provider.missing_settings)}`, tone: "warn" };
    case "running":
      return { label: "Taranıyor…", tone: "neutral" };
    case "ok":
      return { label: `Son tarama başarılı (${provider.last_items_found ?? 0} kayıt)`, tone: "ok" };
    case "empty":
      return { label: "Son tarama boş", tone: "warn" };
    case "error":
      return { label: `Son tarama hatalı: ${provider.last_error ?? "bilinmeyen hata"}`, tone: "danger" };
    case "ready":
      return { label: "Hazır", tone: "ok" };
    default:
      return { label: "Henüz çalışmadı", tone: "neutral" };
  }
}

/** "N kullanılabilir · M yapılandırılmamış · ..." kirilimi. "0 saglikli"
 *  gibi tum saglayicilari bozuk gosteren bir ifade uretmez. */
function statusBreakdown(providers: MediaProviderStatus[]): string {
  const missing = providers.filter((provider) => provider.state === "missing_settings").length;
  const parts = [`${providers.length - missing} kullanılabilir`];
  if (missing > 0) parts.push(`${missing} yapılandırılmamış`);
  for (const [state, label] of Object.entries(STATE_SUMMARY)) {
    const count = providers.filter((provider) => provider.state === state).length;
    if (count > 0) parts.push(`${label}: ${count}`);
  }
  return parts.join(" · ");
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

  const providers = useQuery({
    queryKey: ["media-providers"],
    queryFn: () => api.get<MediaProviderStatus[]>("/media/providers"),
  });
  const sync = useMutation({
    mutationFn: () => api.post("/media/sync"),
    onSuccess: () => invalidateAfter("source.sync"),
  });

  const data = providers.data ?? [];
  const lastRun = latestRun(data);
  const failed = providers.isError;
  const running = data.some((provider) => provider.state === "running");

  useEffect(() => {
    if (failed && !wasProviderError.current) setOpen(true);
    wasProviderError.current = failed;
  }, [failed]);

  return (
    <details
      data-media-sync
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
      className="overflow-hidden rounded-card border border-subtle bg-surface"
    >
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3.5 py-2.5 marker:content-none">
        <ChevronDown
          className={cx("shrink-0 transition-transform", open && "rotate-180")}
          size={15}
          aria-hidden="true"
        />
        <span className="text-body font-medium text-primary">Kaynak ayrıntıları</span>
        {providers.isLoading ? (
          <span className="ml-auto text-meta text-muted" aria-live="polite">
            Kaynaklar yükleniyor…
          </span>
        ) : failed ? (
          <span className="ml-auto text-meta text-danger">Kaynak verisi alınamadı</span>
        ) : (
          <span
            className="ml-auto flex flex-wrap items-center justify-end gap-2 text-meta text-muted"
            aria-live="polite"
          >
            <span>{data.length} kaynak</span>
            {data.length > 0 && <span>{statusBreakdown(data)}</span>}
            {lastRun && <span>son çekim {relativeTime(lastRun)}</span>}
          </span>
        )}
      </summary>

      <div className="border-t border-subtle">
        {failed ? (
          <div role="alert" className="flex flex-wrap items-center gap-3 px-3.5 py-3 text-meta text-danger">
            <span>Medya sağlayıcıları yüklenemedi: {providers.error.message}</span>
            <Button
              size="sm"
              disabled={providers.isFetching}
              onClick={() => {
                void providers.refetch();
              }}
            >
              Yeniden dene
            </Button>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-subtle px-3.5 py-2.5">
              <p className="text-meta text-secondary">Tüm sağlayıcılar arka planda kuyruğa alınır.</p>
              <Button size="sm" disabled={!online || sync.isPending || running} onClick={() => sync.mutate()}>
                <RefreshCw
                  size={13}
                  aria-hidden="true"
                  className={sync.isPending || running ? "animate-spin" : undefined}
                />{" "}
                Şimdi tara
              </Button>
            </div>

            {sync.error && (
              <p role="alert" className="border-b border-subtle px-3.5 py-2 text-meta text-danger">
                Tarama kuyruğa alınamadı: {sync.error.message}. Lütfen tekrar deneyin.
              </p>
            )}

            {providers.isLoading ? null : data.length === 0 ? (
              <div className="px-3.5">
                <Empty variant="inline">
                  Yapılandırılmış medya sağlayıcısı yok.{" "}
                  <a href="#/settings?section=media-links" className="text-accent hover:underline">
                    Sağlayıcı anahtarlarını aç
                  </a>
                </Empty>
              </div>
            ) : (
              <ul>
                {data.map((provider) => {
                  const status = providerStatus(provider);
                  return (
                    <li
                      key={provider.id}
                      className="grid gap-1 border-b border-subtle px-3.5 py-2.5 last:border-b-0 sm:grid-cols-[minmax(0,1fr)_auto] sm:gap-x-3"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-body text-primary">{providerLabel(provider.id) ?? provider.id}</p>
                        <p className="truncate text-meta text-secondary">{providerKinds(provider)}</p>
                      </div>
                      <div className="flex flex-wrap items-start gap-2 sm:justify-end">
                        <span className={cx("break-words text-meta", STATUS_TONE[status.tone])} title={status.label}>
                          {status.label}
                        </span>
                        {provider.last_run_at && (
                          <span className="text-meta text-muted">{relativeTime(provider.last_run_at)}</span>
                        )}
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
