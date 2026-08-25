import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { components } from "@/generated/api-schema";
import { Button, Empty, PageFrame, PageHeader, RowList, Section, Stat, cx } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { MediaMetrics } from "./MediaPosterGrid";
import { Cover, KIND_LABELS, mediaCoverUrl, mediaProvider, providerChip, providerLabel, statusLabel } from "./shared";

type MediaDashboard = components["schemas"]["MediaDashboardOut"];
type MediaUnit = components["schemas"]["MediaUnitOut"];

function durationLabel(totalMinutes: number | null | undefined): string {
  if (!totalMinutes) return "—";
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours === 0) return `${minutes} dk`;
  return minutes === 0 ? `${hours} sa` : `${hours} sa ${minutes} dk`;
}

function unitRow(unit: MediaUnit) {
  return (
    <li key={unit.id} className="flex flex-wrap items-center gap-3 py-2">
      <Cover url={unit.cover_url ?? null} title={unit.title} size="h-12 w-9" />
      <div className="min-w-0 flex-1">
        <a
          href={`#/media/${encodeURIComponent(unit.media_id)}`}
          aria-label={`${unit.title} kaydını aç`}
          className="block truncate text-body font-medium text-primary hover:text-accent hover:underline"
        >
          {unit.number != null ? `${unit.number}. ` : ""}
          {unit.title}
        </a>
        {unit.release_at && (
          <p className="mt-0.5 text-meta text-muted">
            {new Date(unit.release_at).toLocaleDateString("tr-TR", { day: "numeric", month: "long" })}
            {unit.duration_min != null ? ` · ${unit.duration_min} dk` : ""}
          </p>
        )}
      </div>
    </li>
  );
}

export function MediaStatsPage() {
  const online = useOnline();
  const {
    data: dashboard,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["media-dashboard"],
    queryFn: () => api.get<MediaDashboard>("/media/dashboard"),
  });

  return (
    <PageFrame className="space-y-6">
      <PageHeader eyebrow="Takip" title="Medya özeti" />

      {isLoading ? (
        <p role="status" className="text-meta text-muted">
          Medya özeti yükleniyor…
        </p>
      ) : isError ? (
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
          Medya özeti yüklenemedi: {error.message}
        </Empty>
      ) : dashboard?.stats ? (
        <>
          <div className="space-y-2">
            <MediaMetrics stats={dashboard.stats} />
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Stat label="Toplam süre" value={durationLabel(dashboard.stats.total_duration_min)} />
              <Stat label="Puanlanan kayıt" value={dashboard.stats.scored_count} />
              <Stat
                label="Ortalama puan"
                value={dashboard.stats.average_score == null ? "—" : `${dashboard.stats.average_score} / 10`}
              />
              <Stat label="Tür dağılımı" value={Object.keys(dashboard.stats.by_kind).length} />
            </div>
            {Object.keys(dashboard.stats.by_kind).length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(dashboard.stats.by_kind).map(([kind, count]) => (
                  <span key={kind} className={cx("rounded border px-2 py-0.5 text-micro text-secondary")}>
                    {KIND_LABELS[kind] ?? kind} <span className="numeral opacity-70">{count}</span>
                  </span>
                ))}
              </div>
            )}
          </div>

          <Section title="Devam edenler">
            {dashboard.continue_items.length === 0 ? (
              <Empty>Devam eden kayıt yok.</Empty>
            ) : (
              <RowList as="ul">
                {dashboard.continue_items.map((item) => (
                  <li key={item.id} className="flex flex-wrap items-center gap-3 py-2">
                    <Cover url={mediaCoverUrl(item)} title={item.title} size="h-12 w-9" />
                    <div className="min-w-0 flex-1">
                      <a
                        href={`#/media/${encodeURIComponent(item.id)}`}
                        aria-label={`${item.title} detayını aç`}
                        className="block truncate text-body font-medium text-primary hover:text-accent hover:underline"
                      >
                        {item.title}
                      </a>
                      <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-meta text-muted">
                        <span>{statusLabel(item.kind, item.status)}</span>
                        {mediaProvider(item) && (
                          <span className={cx("rounded border px-1.5 py-px", providerChip(mediaProvider(item)))}>
                            {providerLabel(mediaProvider(item))}
                          </span>
                        )}
                      </p>
                    </div>
                    {item.progress != null && (
                      <span className="shrink-0 numeral text-meta text-secondary">
                        {item.progress}
                        {item.total != null ? ` / ${item.total}` : ""}
                      </span>
                    )}
                  </li>
                ))}
              </RowList>
            )}
          </Section>

          <Section title="Yaklaşan">
            {dashboard.upcoming.length === 0 ? (
              <Empty>Yaklaşan içerik yok.</Empty>
            ) : (
              <RowList as="ul">{dashboard.upcoming.map(unitRow)}</RowList>
            )}
          </Section>

          <Section title="Son tüketimler">
            {dashboard.recent_consumptions.length === 0 ? (
              <Empty>Henüz tüketim kaydı yok.</Empty>
            ) : (
              <RowList as="ul">
                {dashboard.recent_consumptions.map((entry) => (
                  <li key={entry.id} className="flex flex-wrap items-center gap-3 py-2">
                    <span className="min-w-0 flex-1 text-body text-secondary">
                      {entry.action} · {entry.amount ?? 0} {entry.measure ?? "öğe"}
                    </span>
                    <span className="text-meta text-muted">
                      {new Date(entry.occurred_at ?? entry.created_at ?? Date.now()).toLocaleString("tr-TR", {
                        day: "numeric",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </li>
                ))}
              </RowList>
            )}
          </Section>
        </>
      ) : null}

      {!online && <p className="text-meta text-muted">Çevrimdışısın — özet salt okunur.</p>}
    </PageFrame>
  );
}
