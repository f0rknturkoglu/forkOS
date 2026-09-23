import { useMutation, useQuery } from "@tanstack/react-query";
import { BellRing, CalendarClock, CalendarPlus } from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { api, qs } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import type { MediaPage as MediaPageResponse, MediaProviderStatus } from "@/core/types";
import { Button, Chip, Empty, FilterChip, PageFrame, RowList, Section, Select, cx } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { daysBetween, localDateKey, todayKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import type { components } from "@/generated/api-schema";
import { Cover, KINDS, KIND_LABELS, providerChip, providerLabel } from "./shared";

type UpcomingEntry = components["schemas"]["MediaUpcomingOut"];
type UpcomingPage = components["schemas"]["MediaUpcomingPageOut"];

const DAY_OPTIONS = [7, 30, 90] as const;
const DEFAULT_DAYS = 30;

/** Unit olcu tipi -> kullanici dili ("#4 bölüm"). */
const UNIT_TYPE_LABELS: Record<string, string> = {
  episode: "bölüm",
  chapter: "bölüm",
  track: "parça",
  page: "sayfa",
  item: "kayıt",
  minute: "dakika",
  hour: "saat",
};

type GroupKey = "today" | "week" | "month" | "later";
const GROUPS: { key: GroupKey; label: string }[] = [
  { key: "today", label: "Bugün" },
  { key: "week", label: "Bu hafta" },
  { key: "month", label: "Bu ay" },
  { key: "later", label: "Daha sonra" },
];

/** Yerel gune gore grup: Bugun / Bu hafta (7 gun) / Bu ay (30 gun) / Daha sonra. */
function groupFor(releaseAt: string): GroupKey {
  const date = new Date(releaseAt);
  if (Number.isNaN(date.getTime())) return "later";
  const delta = daysBetween(todayKey(), localDateKey(date));
  if (delta <= 0) return "today";
  if (delta <= 7) return "week";
  if (delta <= 30) return "month";
  return "later";
}

function releaseRelative(releaseAt: string): string {
  const date = new Date(releaseAt);
  if (Number.isNaN(date.getTime())) return "Tarih yok";
  const delta = daysBetween(todayKey(), localDateKey(date));
  if (delta <= 0) return "Bugün";
  if (delta === 1) return "Yarın";
  if (delta < 30) return `${delta} gün sonra`;
  return `${Math.round(delta / 30)} ay sonra`;
}

function releaseDate(releaseAt: string): string {
  const date = new Date(releaseAt);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
}

/** Secimler URL'de tutulur; varsayilan deger parametreyi temizler. */
function setFilterParams(route: { path: string; params: URLSearchParams }, patch: Record<string, string | null>): void {
  const params = new URLSearchParams(route.params);
  for (const [key, value] of Object.entries(patch)) {
    if (value) params.set(key, value);
    else params.delete(key);
  }
  const serialized = params.toString();
  navigate(serialized ? `${route.path}?${serialized}` : route.path, { replace: true });
}

/** "Saglayici hic taranmadi" ayrimi: hicbir saglayicinin son calismasi yok. */
function neverScanned(provider: MediaProviderStatus): boolean {
  return provider.last_run_at == null;
}

export function MediaUpcomingPage() {
  const online = useOnline();
  const route = useHashRoute();
  const days = DAY_OPTIONS.find((option) => String(option) === route.params.get("days")) ?? DEFAULT_DAYS;
  const kind = route.params.get("kind") ?? "";
  const provider = route.params.get("provider") ?? "";

  const providers = useQuery({
    queryKey: ["media-providers"],
    queryFn: () => api.get<MediaProviderStatus[]>("/media/providers"),
  });
  const { data, isLoading, isFetching, isError, error, refetch } = useQuery({
    queryKey: ["media", "upcoming", { days, kind, provider }],
    queryFn: () =>
      api.get<UpcomingPage>(
        `/media/upcoming${qs({
          days,
          kind: kind || undefined,
          provider: provider || undefined,
        })}`,
      ),
  });

  const entries = data?.entries ?? [];

  // Bos durum ayrimi: hic takip edilen kayit yok mu? (yalnizca gerektiginde sorulur.)
  const monitored = useQuery({
    queryKey: ["media", "monitored-count"],
    queryFn: () => api.get<MediaPageResponse>("/media?monitored=true&limit=1"),
    enabled: !isLoading && !isError && entries.length === 0,
  });

  const plan = useMutation({
    // PlanSlotIn.day ZORUNLU: gun gonderilmezse API 422 doner.
    mutationFn: (entry: UpcomingEntry) => api.post("/plan", { entity_id: entry.media_id, day: todayKey() }),
    onSuccess: () => invalidateAfter("plan.write"),
  });
  const monitor = useMutation({
    mutationFn: (entry: UpcomingEntry) =>
      api.patch(`/media/${encodeURIComponent(entry.media_id)}`, { monitored: !entry.monitored }),
    onSuccess: () => invalidateAfter("media.write"),
  });

  const providerList = providers.data ?? [];
  const noMonitored = monitored.data != null && monitored.data.total === 0;
  const providersNeverScanned = providerList.length > 0 && providerList.every(neverScanned);

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Medya"
          title="Yaklaşan yayınlar"
          hint={data ? `${data.total} yayın` : undefined}
        />
        <WorkspaceScrollArea className="space-y-4 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <div role="group" aria-label="Yayın aralığı" className="flex flex-wrap gap-1.5">
              {DAY_OPTIONS.map((option) => (
                <FilterChip
                  key={option}
                  label={`${option} gün`}
                  active={days === option}
                  onClick={() => setFilterParams(route, { days: option === DEFAULT_DAYS ? null : String(option) })}
                />
              ))}
            </div>
            <Select
              value={kind}
              ariaLabel="Tür filtresi"
              onChange={(value) => setFilterParams(route, { kind: value || null })}
            >
              <option value="">Tüm türler</option>
              {KINDS.map((value) => (
                <option key={value} value={value}>
                  {KIND_LABELS[value] ?? value}
                </option>
              ))}
            </Select>
            <Select
              value={provider}
              ariaLabel="Sağlayıcı filtresi"
              onChange={(value) => setFilterParams(route, { provider: value || null })}
            >
              <option value="">Tüm sağlayıcılar</option>
              {providerList.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {providerLabel(entry.id) ?? entry.id}
                </option>
              ))}
            </Select>
          </div>

          {isLoading ? (
            <p role="status" className="text-meta text-muted">
              Yaklaşan yayınlar yükleniyor…
            </p>
          ) : isError ? (
            <div role="alert">
              <Empty
                variant="page"
                action={
                  <Button
                    size="sm"
                    disabled={isFetching}
                    onClick={() => {
                      void refetch();
                    }}
                  >
                    Yeniden dene
                  </Button>
                }
              >
                Yayınlar alınamadı: {error.message}
              </Empty>
            </div>
          ) : entries.length === 0 ? (
            monitored.isLoading ? (
              <p role="status" className="text-meta text-muted">
                Takip durumu kontrol ediliyor…
              </p>
            ) : noMonitored ? (
              <Empty
                variant="page"
                action={
                  <Button size="sm" onClick={() => navigate("/media")}>
                    Kütüphaneyi aç
                  </Button>
                }
              >
                Takip edilen medya yok. Bir kaydı açıp "Yeni yayınları takip et"i aç.
              </Empty>
            ) : providersNeverScanned ? (
              <Empty
                variant="page"
                action={
                  <Button size="sm" onClick={() => navigate("/media")}>
                    Kütüphaneyi aç
                  </Button>
                }
              >
                Sağlayıcı henüz taranmadı; "Şimdi tara" ile başlat.
              </Empty>
            ) : (
              <Empty>Önümüzdeki {days} gün içinde yayın yok.</Empty>
            )
          ) : (
            <div className="space-y-4">
              {GROUPS.map((group) => {
                const rows = entries.filter((entry) => groupFor(entry.release_at) === group.key);
                if (rows.length === 0) return null;
                return (
                  <Section key={group.key} title={group.label} hint={`${rows.length} yayın`}>
                    <RowList as="ul">
                      {rows.map((entry) => (
                        <li
                          key={`${entry.entry_type}-${entry.entity_id}`}
                          className="flex flex-wrap items-center gap-3 py-2.5"
                        >
                          <Cover url={entry.cover_url ?? null} title={entry.media_title} size="h-16 w-11" />
                          <div className="min-w-0 flex-1">
                            <a
                              href={`#/media/${encodeURIComponent(entry.media_id)}`}
                              aria-label={`${entry.media_title} kaydını aç`}
                              className="block truncate text-body font-medium text-primary hover:text-accent hover:underline"
                            >
                              {entry.media_title}
                            </a>
                            {entry.entry_type === "unit" && (
                              <p className="truncate text-meta text-secondary" title={entry.title}>
                                {entry.title}
                                {entry.number != null && (
                                  <>
                                    {" "}
                                    · #{entry.number} {UNIT_TYPE_LABELS[entry.unit_type ?? ""] ?? entry.unit_type}
                                  </>
                                )}
                              </p>
                            )}
                            <div className="mt-1 flex flex-wrap items-center gap-1.5 text-meta text-muted">
                              <Chip identity={"kind-" + entry.kind} variant="outline" size="xs">
                                {KIND_LABELS[entry.kind] ?? entry.kind}
                              </Chip>
                              {entry.provider && (
                                <span className={cx("rounded border px-1.5 py-px", providerChip(entry.provider))}>
                                  {providerLabel(entry.provider)}
                                </span>
                              )}
                              <span className="inline-flex items-center gap-1">
                                <CalendarClock size={13} aria-hidden="true" />
                                {releaseRelative(entry.release_at)} · {releaseDate(entry.release_at)}
                              </span>
                              {entry.monitored && (
                                <Chip tone="ok" size="xs" icon={<BellRing size={11} aria-hidden="true" />}>
                                  Takip ediliyor
                                </Chip>
                              )}
                            </div>
                          </div>
                          <span className="flex shrink-0 flex-wrap items-center gap-1.5">
                            <Button
                              size="sm"
                              disabled={!online || plan.isPending}
                              onClick={() => plan.mutate(entry)}
                              ariaLabel={`${entry.media_title} kaydını bugüne ekle`}
                            >
                              <CalendarPlus size={13} aria-hidden="true" /> Bugüne ekle
                            </Button>
                            <Button
                              size="sm"
                              disabled={!online || monitor.isPending}
                              onClick={() => monitor.mutate(entry)}
                              ariaLabel={`${entry.media_title} takibini ${entry.monitored ? "kapat" : "aç"}`}
                            >
                              {entry.monitored ? "Takibi kapat" : "Takibi aç"}
                            </Button>
                          </span>
                        </li>
                      ))}
                    </RowList>
                  </Section>
                );
              })}
            </div>
          )}

          {plan.error && (
            <p role="alert" className="text-meta text-danger">
              Bugüne eklenemedi: {plan.error.message}
            </p>
          )}
          {monitor.error && (
            <p role="alert" className="text-meta text-danger">
              Takip durumu değiştirilemedi: {monitor.error.message}
            </p>
          )}
          {!online && <p className="text-meta text-muted">Çevrimdışısın — yayınlar salt okunur.</p>}
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
