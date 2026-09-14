import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Flame, Github, MessageSquare, Rss, Star, TrendingUp } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api, qs } from "@/core/api";
import { Button, RowList, Section, cx, hostOf, relativeTime } from "@/core/ui";
import { navigate } from "@/app/router";
import type { FeedItem, RedditPost, RssStats } from "@/core/types";

type Origin = "rss" | "reddit" | "hn" | "gh";

/**
 * Kaynak kimligi: ikon + renk. Renkler markadan gelir (semantik degil),
 * index.css'te --feed-* olarak tanimli.
 */
const ORIGIN: Record<Origin, { icon: LucideIcon; text: string }> = {
  rss: { icon: Rss, text: "text-feed-rss" },
  reddit: { icon: MessageSquare, text: "text-feed-reddit" },
  hn: { icon: Flame, text: "text-feed-hn" },
  gh: { icon: Github, text: "text-feed-gh" },
};

interface StreamItem {
  key: string;
  origin: Origin;
  title: string;
  /** RSS satiri yerel okuyucuya gider (href yok), otekiler disariya. */
  href: string | null;
  source: string;
  subtitle: string | null;
  host: string | null;
  score: number | null;
  scoreIcon: "points" | "stars" | null;
  commentsUrl: string | null;
  at: number;
  unread: boolean;
}

interface HnStory {
  objectID: string;
  title: string;
  url: string | null;
  points: number | null;
  num_comments: number | null;
  created_at: string;
}

interface Repo {
  full_name: string;
  html_url: string;
  description: string | null;
  stargazers_count: number;
  language: string | null;
  created_at: string;
}

const HN_ITEM = "https://news.ycombinator.com/item?id=";
const STREAM_LIMIT = 15;

const FILTERS: { id: "all" | Origin; label: string }[] = [
  { id: "all", label: "tümü" },
  { id: "rss", label: "RSS" },
  { id: "reddit", label: "Reddit" },
  { id: "hn", label: "HN" },
  { id: "gh", label: "GitHub" },
];

/**
 * Hibrit akis: kendi RSS beslemelerin + tech/CS subredditleri + Hacker News
 * ana sayfasi + haftanin GitHub repolari, tek listede. Dordu de ayni soruyu
 * cevapliyor -- "bugun okunacak ne var?" -- o yuzden ayri kutular degil tek
 * akis; hepsi zamana gore siralaniyor.
 *
 * Dış haber kaynaklarının tamamı backend'den geçer; böylece source_run sağlık
 * kaydı, timeout ve çevrimdışı PWA önbelleği tek yerde uygulanır.
 */
export function FeedStreamWidget() {
  const [filter, setFilter] = useState<"all" | Origin>("all");

  const rssQuery = useQuery({
    queryKey: ["items", "panel"],
    queryFn: () => api.get<FeedItem[]>(`/rss/items${qs({ limit: 15 })}`),
  });
  const rss = rssQuery.data ?? [];
  const { data: stats } = useQuery({
    queryKey: ["rss-stats"],
    queryFn: () => api.get<RssStats>("/rss/stats"),
  });
  const redditQuery = useQuery({
    queryKey: ["reddit-news"],
    queryFn: () => api.get<RedditPost[]>(`/news/reddit${qs({ limit: 15 })}`),
    refetchInterval: 15 * 60_000,
    staleTime: 10 * 60_000,
    retry: 1,
  });
  const reddit = redditQuery.data ?? [];
  const hnQuery = useQuery({
    queryKey: ["hacker-news"],
    queryFn: () => api.get<HnStory[]>("/news/hacker-news?limit=15"),
    refetchInterval: 15 * 60_000,
    staleTime: 10 * 60_000,
  });
  const hn = hnQuery.data ?? [];
  const githubQuery = useQuery({
    queryKey: ["github-trending"],
    queryFn: () => api.get<Repo[]>("/news/github-trending?limit=10"),
    refetchInterval: 6 * 3600_000,
    staleTime: 3 * 3600_000,
  });
  const repos = githubQuery.data ?? [];
  const sourceQueries = { rss: rssQuery, reddit: redditQuery, hn: hnQuery, gh: githubQuery };

  const failures = [
    { origin: "rss" as const, label: "RSS", failed: rssQuery.isError, retry: () => rssQuery.refetch() },
    { origin: "reddit" as const, label: "Reddit", failed: redditQuery.isError, retry: () => redditQuery.refetch() },
    { origin: "hn" as const, label: "Hacker News", failed: hnQuery.isError, retry: () => hnQuery.refetch() },
    { origin: "gh" as const, label: "GitHub", failed: githubQuery.isError, retry: () => githubQuery.refetch() },
  ].filter((source) => source.failed && (filter === "all" || filter === source.origin));

  // Kaynak basina kota: RSS dakikada akarken otekiler saatlik/gunluk. Duz zaman
  // siralamasi yapinca digerleri listeden tamamen dusuyor -- once her
  // kaynaktan esit sayida alinir, sonra kendi aralarinda siralanir.
  const perSource = filter === "all" ? 4 : 15;

  // Ayni besleme arka arkaya on yazi birakinca panel tek feed'e donuyor.
  // Panel bir ozet: besleme basina en fazla iki yazi, gerisi okuyucuda.
  const perFeed = filter === "rss" ? 3 : 2;
  const seen = new Map<string, number>();
  const rssTop = rss.filter((item) => {
    const count = seen.get(item.feed_id) ?? 0;
    if (count >= perFeed) return false;
    seen.set(item.feed_id, count + 1);
    return true;
  });

  const items: StreamItem[] = [
    ...rssTop.slice(0, perSource).map((item) => ({
      key: `rss-${item.id}`,
      origin: "rss" as const,
      title: item.title,
      href: null,
      source: item.feed_title,
      subtitle: null,
      host: null,
      score: null,
      scoreIcon: null,
      commentsUrl: null,
      at: new Date(item.published_at ?? item.fetched_at).getTime(),
      unread: item.read_at === null,
    })),
    ...reddit.slice(0, perSource).map((post) => ({
      key: `reddit-${post.id}`,
      origin: "reddit" as const,
      title: post.title,
      href: post.url,
      source: post.subreddit ? `r/${post.subreddit}` : "reddit",
      subtitle: null,
      host: post.url === post.comments_url ? null : hostOf(post.url),
      score: null,
      scoreIcon: null,
      commentsUrl: post.comments_url,
      at: post.published_at ? new Date(post.published_at).getTime() : 0,
      unread: false,
    })),
    ...hn.slice(0, perSource).map((story) => ({
      key: `hn-${story.objectID}`,
      origin: "hn" as const,
      title: story.title,
      href: story.url ?? HN_ITEM + story.objectID,
      source: "Hacker News",
      subtitle: null,
      host: story.url ? hostOf(story.url) : null,
      score: story.points,
      scoreIcon: "points" as const,
      commentsUrl: HN_ITEM + story.objectID,
      at: new Date(story.created_at).getTime(),
      unread: false,
    })),
    ...repos.slice(0, perSource).map((repo) => ({
      key: `gh-${repo.full_name}`,
      origin: "gh" as const,
      title: repo.full_name,
      href: repo.html_url,
      source: repo.language ?? "GitHub",
      subtitle: repo.description,
      host: null,
      score: repo.stargazers_count,
      scoreIcon: "stars" as const,
      commentsUrl: null,
      at: new Date(repo.created_at).getTime(),
      unread: false,
    })),
  ]
    .filter((item) => filter === "all" || item.origin === filter)
    .sort((a, b) => b.at - a.at)
    .slice(0, STREAM_LIMIT);
  const selectedIsLoading =
    filter === "all" ? Object.values(sourceQueries).some((query) => query.isLoading) : sourceQueries[filter].isLoading;

  return (
    <Section
      title="Okuma akışı"
      hint={
        <span className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
          {FILTERS.map((option) => (
            <button
              key={option.id}
              type="button"
              aria-pressed={filter === option.id}
              onClick={() => setFilter(option.id)}
              className={cx(
                "border-b transition",
                filter === option.id
                  ? "border-accent text-primary"
                  : "border-transparent text-muted hover:text-primary",
              )}
            >
              {option.label}
            </button>
          ))}
        </span>
      }
      action={
        <a href="#/rss" className="text-meta text-accent hover:underline">
          {stats?.unread ? `${stats.unread} okunmamış` : "okuyucu"} →
        </a>
      }
      bodyClassName="px-3.5 py-1"
    >
      {failures.length > 0 && (
        <div className="mb-1 flex flex-wrap items-center gap-2 border-b border-warn-border px-2 py-2 text-meta text-warn">
          {failures.map((source) => (
            <span key={source.origin} className="inline-flex items-center gap-1.5">
              {source.label} alınamadı.
              <Button
                size="sm"
                variant="ghost"
                ariaLabel={`${source.label}'i yeniden dene`}
                onClick={() => void source.retry()}
                className="h-auto px-1.5 py-0.5 text-warn"
              >
                yeniden dene
              </Button>
            </span>
          ))}
        </div>
      )}
      {items.length === 0 && selectedIsLoading ? (
        <p className="px-2 py-4 text-center text-meta text-muted">Akış yükleniyor…</p>
      ) : items.length === 0 ? (
        <p className="px-2 py-4 text-center text-meta text-muted">Yeni bir şey yok.</p>
      ) : (
        <RowList>
          {items.map((item) => {
            const skin = ORIGIN[item.origin];
            const Icon = skin.icon;
            return (
              <div key={item.key} className="flex items-start gap-2.5 py-2">
                <Icon size={13} className={cx("mt-1 shrink-0", skin.text)} />
                <div className="min-w-0 flex-1">
                  {item.href ? (
                    <a
                      href={item.href}
                      target="_blank"
                      rel="noreferrer"
                      className="line-clamp-2 text-body font-medium text-primary hover:text-accent"
                    >
                      {item.title}
                    </a>
                  ) : (
                    <button
                      type="button"
                      onClick={() => navigate("/rss")}
                      className={cx(
                        "block w-full truncate text-left text-body hover:text-accent",
                        item.unread ? "font-medium text-primary" : "text-secondary",
                      )}
                    >
                      {item.title}
                    </button>
                  )}
                  {item.subtitle && <p className="mt-0.5 line-clamp-1 text-meta text-secondary">{item.subtitle}</p>}
                  <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-meta text-muted">
                    <span className={cx("rounded border border-subtle px-1.5 py-0.5 text-micro leading-4", skin.text)}>
                      {item.source}
                    </span>
                    {item.host && <span className="max-w-[40%] truncate">{item.host}</span>}
                    {item.score !== null && (
                      <span className="flex items-center gap-1">
                        {item.scoreIcon === "stars" ? <Star size={11} /> : <TrendingUp size={11} />}
                        {item.score}
                      </span>
                    )}
                    {item.commentsUrl && (
                      <a href={item.commentsUrl} target="_blank" rel="noreferrer" className="hover:text-primary">
                        yorumlar
                      </a>
                    )}
                    {item.at > 0 && <span>{relativeTime(new Date(item.at).toISOString())}</span>}
                  </p>
                </div>
              </div>
            );
          })}
        </RowList>
      )}
    </Section>
  );
}
