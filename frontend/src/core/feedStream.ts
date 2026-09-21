/**
 * Okuma akışı — RSS + Reddit + Hacker News + GitHub Trending TEK listede.
 *
 * Dört kaynak da aynı soruyu cevaplıyor ("bugün okunacak ne var?"), bu yüzden
 * ayrı kutular değil tek akış. Bu modül akışın TEK uygulamasıdır: Home widget'ı
 * (`today.feed-stream`) ve Okuma Akışı sayfası (`/feed`) aynı sorguları,
 * aynı birleştirme/kota kurallarını ve aynı hata semantiğini paylaşır.
 *
 * Dış kaynakların tamamı backend'den geçer: source_run sağlık kaydı, timeout,
 * çevrimdışı PWA önbelleği ve hız sınırı tek yerde uygulanır.
 */
import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { useRssStats } from "@/core/runtimeQueries";
import { hostOf } from "@/core/ui";
import type { FeedItem, RedditPost } from "@/core/types";

export type FeedOrigin = "rss" | "reddit" | "hn" | "gh";
export type FeedFilter = "all" | FeedOrigin;

export interface StreamItem {
  key: string;
  origin: FeedOrigin;
  title: string;
  /** RSS satırı yerel okuyucuya gider (href yok), ötekiler dışarıya. */
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

/** Akışta gösterilecek azami satır. */
const FEED_STREAM_LIMIT = 15;

/** Kaynak başına yoklama kotası; sayfa biraz daha geniş liste ister. */
const PAGE_SIZE = {
  rss: 20,
  reddit: 25,
  hn: 25,
  gh: 15,
} as const;

export const FEED_FILTERS: { id: FeedFilter; label: string }[] = [
  { id: "all", label: "Tümü" },
  { id: "rss", label: "RSS" },
  { id: "reddit", label: "Reddit" },
  { id: "hn", label: "Hacker News" },
  { id: "gh", label: "GitHub" },
];

interface FeedSource {
  origin: FeedOrigin;
  label: string;
  failed: boolean;
  retry: () => void;
}

interface FeedStreamState {
  filter: FeedFilter;
  items: StreamItem[];
  sources: FeedSource[];
  failures: FeedSource[];
  /** Seçili filtrenin verisi hâlâ yükleniyor mu. */
  loading: boolean;
  unread: number | null;
}

/** Akışın veri katmanı: iki yüzey de bunu kullanır (§10). */
export function useFeedStream(filter: FeedFilter): FeedStreamState {
  const rssQuery = useQuery({
    queryKey: ["items", "panel"],
    queryFn: () => api.get<FeedItem[]>(`/rss/items${qs({ limit: PAGE_SIZE.rss })}`),
  });
  // RSS ozeti PAYLASILAN hook'tan gelir: ayni ucun ikinci bir anahtari olmaz.
  const statsQuery = useRssStats();
  const redditQuery = useQuery({
    queryKey: ["reddit-news"],
    queryFn: () => api.get<RedditPost[]>(`/news/reddit${qs({ limit: PAGE_SIZE.reddit })}`),
    refetchInterval: 15 * 60_000,
    staleTime: 10 * 60_000,
    retry: 1,
  });
  const hnQuery = useQuery({
    queryKey: ["hacker-news"],
    queryFn: () => api.get<HnStory[]>(`/news/hacker-news${qs({ limit: PAGE_SIZE.hn })}`),
    refetchInterval: 15 * 60_000,
    staleTime: 10 * 60_000,
  });
  const githubQuery = useQuery({
    queryKey: ["github-trending"],
    queryFn: () => api.get<Repo[]>(`/news/github-trending${qs({ limit: PAGE_SIZE.gh })}`),
    refetchInterval: 6 * 3600_000,
    staleTime: 3 * 3600_000,
  });

  const queries = { rss: rssQuery, reddit: redditQuery, hn: hnQuery, gh: githubQuery };
  const sources: FeedSource[] = [
    { origin: "rss", label: "RSS", failed: rssQuery.isError, retry: () => void rssQuery.refetch() },
    { origin: "reddit", label: "Reddit", failed: redditQuery.isError, retry: () => void redditQuery.refetch() },
    { origin: "hn", label: "Hacker News", failed: hnQuery.isError, retry: () => void hnQuery.refetch() },
    { origin: "gh", label: "GitHub", failed: githubQuery.isError, retry: () => void githubQuery.refetch() },
  ];

  // Kaynak başına kota: RSS dakikada akarken diğerleri saatlik/günlük. Düz
  // zaman sıralaması yapınca diğerleri listeden tamamen düşüyor -- önce her
  // kaynaktan eşit sayıda alınır, sonra kendi aralarında sıralanır.
  const perSource = filter === "all" ? 4 : 15;

  // Aynı besleme arka arkaya on yazı bırakınca panel tek feed'e dönüyor:
  // besleme başına en fazla iki (RSS görünümünde üç) yazı.
  const perFeed = filter === "rss" ? 3 : 2;
  const seen = new Map<string, number>();
  const rssTop = (rssQuery.data ?? []).filter((item) => {
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
    ...(redditQuery.data ?? []).slice(0, perSource).map((post) => ({
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
    ...(hnQuery.data ?? []).slice(0, perSource).map((story) => ({
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
    ...(githubQuery.data ?? []).slice(0, perSource).map((repo) => ({
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
    .slice(0, FEED_STREAM_LIMIT);

  return {
    filter,
    items,
    sources,
    failures: sources.filter((source) => source.failed && (filter === "all" || filter === source.origin)),
    loading: filter === "all" ? Object.values(queries).some((query) => query.isLoading) : queries[filter].isLoading,
    unread: statsQuery.data?.unread ?? null,
  };
}
