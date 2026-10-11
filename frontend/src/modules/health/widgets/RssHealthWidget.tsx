import { invalidateAfter } from "@/core/invalidation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { api } from "@/core/api";
import { Button, Chip, Empty, MiniStat, Section, cx, relativeTime, useToast } from "@/core/ui";
import { SectionFallback, dataState } from "@/core/DataState";
import { useRssStats } from "@/core/runtimeQueries";
import { feedStateView, healthSummaryLabel } from "@/core/sourceStatus";
import { useOnline } from "@/lib/hooks";
import type { Feed } from "@/core/types";

/** Durum tonuna gore siralama: ilgi isteyenler ustte. */
const TONE_RANK = { danger: 0, warn: 1, accent: 2, neutral: 3, ok: 4 } as const;

/**
 * RSS besleme sagligi: durum dokumu + tazeleme aksiyonlari.
 *
 * Sinirlar (durustluk kurallari):
 *  - Teshis EDER, kaydi YONETMEZ: silme/duzenleme RSS modulunun isidir; burada
 *    toplu silme yoktur, RSS modulune derin baglanti vardir.
 *  - Durum sozlugu tek kaynaktan gelir (`@/core/sourceStatus`): bilerek kapatilan
 *    besleme "kapali"dir (notr), bozuk degildir; tek bos kosu sorun sayilmaz.
 *  - Sorgu dustugunde/eksik oldugunda "hepsi saglikli" DENMEZ; bilinmeyen durum
 *    acikca yazilir (`SectionFallback`).
 */
export function RssHealthWidget() {
  const online = useOnline();
  const toast = useToast();

  const feedsQuery = useQuery({
    queryKey: ["feeds"],
    queryFn: () => api.get<Feed[]>("/rss/feeds"),
  });
  // Paylasilan uç: anahtar/aralik `core/runtimeQueries`'te tek yerde durur.
  const statsQuery = useRssStats();

  const feeds = feedsQuery.data;
  const stats = statsQuery.data;
  const feedsState = dataState(feedsQuery);
  const statsState = dataState(statsQuery);
  /** YESIL cumle yalniz BILINEN durumda kurulur: NO DATA != HEALTHY. */
  const known = feedsState === "ready" && statsState === "ready";

  const refreshAll = useMutation({
    mutationFn: () => api.post<{ started: number }>("/rss/refresh-all"),
    onSuccess: (result) => {
      invalidateAfter("rss.write");
      toast.push(
        result.started > 0 ? `${result.started} besleme çekiliyor…` : "Süresi gelen besleme yok — hepsi taze.",
        { tone: result.started > 0 ? "neutral" : "ok" },
      );
    },
  });
  const refreshOne = useMutation({
    mutationFn: (id: string) => api.post(`/rss/feeds/${id}/refresh`),
    onSuccess: () => invalidateAfter("rss.write"),
  });

  // Durum tek sozlukten okunur; siralama yalnizca gosterim icin.
  const rows = (feeds ?? [])
    .map((feed) => ({ feed, view: feedStateView(feed) }))
    .sort((a, b) => TONE_RANK[a.view.tone] - TONE_RANK[b.view.tone]);
  const healthy = rows.filter((row) => row.view.tone === "ok").length;
  const attention = rows.filter((row) => row.view.attention).length;
  /** Raporlanacak satirlar: saglikli olanlar listede tekrar edilmez. */
  const listed = rows.filter((row) => row.view.tone !== "ok");

  return (
    <Section
      title="RSS Sağlığı"
      action={
        <div className="flex items-center gap-2">
          {/* Kaydi yonetmek RSS modulunun isidir; saglik yuzeyi yalniz baglantilar. */}
          <a href="#/rss" title="Beslemeleri RSS modülünde yönet" className="text-meta text-accent hover:underline">
            RSS&apos;i yönet →
          </a>
          <Button size="sm" disabled={!online || refreshAll.isPending} onClick={() => refreshAll.mutate()}>
            <RefreshCw size={13} className={refreshAll.isPending ? "animate-spin" : undefined} aria-hidden />
            Tümünü tazele
          </Button>
        </div>
      }
      bodyClassName="stack-y-4"
    >
      {stats ? (
        <div className="grid grid-cols-4 gap-3">
          <MiniStat label="Besleme" value={stats.feeds} />
          <MiniStat label="Aktif" value={stats.active_feeds} tone="ok" />
          {/* Backend `failing_feeds` = hata biriktiren YA DA kapatilmis beslemeler. */}
          <MiniStat label="Hata / kapalı" value={stats.failing_feeds} tone="warn" />
          <MiniStat label="Okunmamış" value={stats.unread} />
        </div>
      ) : (
        <SectionFallback
          state={statsState === "ready" ? "error" : statsState}
          what="RSS özeti"
          onRetry={() => void statsQuery.refetch()}
        />
      )}

      {feeds ? (
        feeds.length === 0 ? (
          <Empty>Kayıtlı besleme yok — RSS modülünden ekleyebilirsin.</Empty>
        ) : known && listed.length === 0 ? (
          <Empty>Bütün beslemeler sağlıklı — hata yok, hepsi çekilmiş.</Empty>
        ) : listed.length > 0 ? (
          <div>
            {known && (
              <p className="mb-2 text-meta text-secondary">
                {healthSummaryLabel({ total: feeds.length, healthy, attention })}
              </p>
            )}
            <ul className="stack-y-1.5">
              {listed.slice(0, 10).map(({ feed, view }) => (
                <li
                  key={feed.id}
                  className="flex items-center gap-2.5 border-b border-subtle px-1 py-2 last:border-b-0"
                >
                  {view.tone !== "neutral" && (
                    <AlertTriangle
                      size={13}
                      aria-hidden
                      className={cx("shrink-0", view.tone === "danger" ? "text-danger" : "text-warn")}
                    />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="max-w-[260px] truncate text-body text-primary">{feed.title}</span>
                      <Chip tone={view.tone}>{view.label}</Chip>
                    </div>
                    {feed.last_fetched_at && (
                      <p className="mt-0.5 text-meta text-muted">son çekim {relativeTime(feed.last_fetched_at)}</p>
                    )}
                  </div>
                  <Button
                    size="sm"
                    disabled={!online || refreshOne.isPending}
                    onClick={() => refreshOne.mutate(feed.id)}
                    title="Bu beslemeyi şimdi çek"
                  >
                    <RefreshCw size={13} aria-hidden /> Çek
                  </Button>
                </li>
              ))}
            </ul>
            {listed.length > 10 && (
              <p className="mt-2 text-meta text-muted">
                +{listed.length - 10} besleme daha — tümünü tazele ile düzeltebilirsin.
              </p>
            )}
          </div>
        ) : null
      ) : (
        <SectionFallback
          state={feedsState === "ready" ? "error" : feedsState}
          what="Besleme listesi"
          onRetry={() => void feedsQuery.refetch()}
        />
      )}
    </Section>
  );
}
