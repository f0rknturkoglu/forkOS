/** Canonical reading feed. Eligibility is established before any provider query mounts. */
import { safeReadingUrl } from "@/core/readerHtml";
import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { useRssStats } from "@/core/runtimeQueries";
import { hostOf } from "@/core/ui";
import type { FeedItem, RedditPost } from "@/core/types";
import { useExperience } from "@/core/onboarding/experience";

export type FeedOrigin = "rss" | "reddit" | "hn" | "gh" | "hf";
export type FeedFilter = "all" | FeedOrigin;
export interface StreamItem {
  key: string;
  origin: FeedOrigin;
  title: string;
  href: string | null;
  source: string;
  subtitle: string | null;
  host: string | null;
  score: number | null;
  scoreIcon: "points" | "stars" | null;
  commentsUrl: string | null;
  commentCount?: number | null;
  at: number;
  unread: boolean;
  entityId?: string;
  savedBookmarkId?: string;
  feedId?: string;
  canonicalUrl?: string | null;
  authors?: string[];
  featuredAt?: string | null;
  paperId?: string;
  arxivUrl?: string;
}
interface HnStory {
  objectID: string;
  title: string;
  url: string | null;
  points: number | null;
  created_at: string;
  num_comments?: number | null;
}
interface Repo {
  full_name: string;
  html_url: string;
  description: string | null;
  stargazers_count: number;
  language: string | null;
  created_at: string;
}
interface Paper {
  id: string;
  title: string;
  url: string;
  authors: string[];
  summary: string | null;
  published_at: string | null;
  featured_at: string | null;
  arxiv_url: string;
  upvotes: number;
  num_comments: number;
}
export const FEED_FILTERS: { id: FeedFilter; label: string }[] = [
  { id: "all", label: "Tümü" },
  { id: "rss", label: "RSS" },
  { id: "reddit", label: "Reddit" },
  { id: "hn", label: "Hacker News" },
  { id: "gh", label: "GitHub · Yeni ve Popüler" },
  { id: "hf", label: "Papers" },
];
const hnItem = "https://news.ycombinator.com/item?id=";
/** Fair round robin: a busy provider cannot erase a quieter provider. URL identity spans providers. */
export function composeFeed(groups: StreamItem[][], limit: number): StreamItem[] {
  const seen = new Set<string>();
  const output: StreamItem[] = [];
  for (let index = 0; index < Math.max(0, ...groups.map((group) => group.length)) && output.length < limit; index++) {
    for (const group of groups) {
      const item = group[index];
      if (!item || output.length >= limit) continue;
      const key = canonicalIdentity(item.canonicalUrl || item.href || item.key);
      if (!seen.has(key)) {
        seen.add(key);
        output.push(item);
      }
    }
  }
  return output;
}
function canonicalIdentity(value: string) {
  try {
    const url = new URL(value);
    url.hash = "";
    const paper =
      (url.hostname === "arxiv.org" || url.hostname === "huggingface.co") &&
      url.pathname.match(/^\/(?:abs|papers)\/(\d{4}\.\d{4,5})(?:v\d+)?$/);
    if (paper) return "paper:" + paper[1];
    for (const key of [...url.searchParams.keys()])
      if (key.startsWith("utm_") || key === "ref") url.searchParams.delete(key);
    return url.href.replace(/\/$/, "");
  } catch {
    return value;
  }
}
export function useFeedStream(filter: FeedFilter, options: { limit?: number; bundleId?: string; date?: string } = {}) {
  const experience = useExperience();
  const prefs = experience.isError ? undefined : experience.data?.feed;
  const bundle = prefs?.bundles.find((item) => item.id === options.bundleId);
  const eligible = (origin: FeedOrigin) =>
    Boolean(
      prefs &&
      (origin === "rss" ? prefs.rss_enabled : prefs.providers.includes(origin)) &&
      (filter === "all" || filter === origin) &&
      (!bundle || bundle.channels.includes(origin) || (origin === "rss" && bundle.feed_ids.length > 0)),
    );
  const rss = useQuery({
    queryKey: ["items", "panel", 100],
    queryFn: () => api.get<FeedItem[]>(`/rss/items${qs({ limit: 100 })}`),
    enabled: eligible("rss"),
    staleTime: 60_000,
  });
  const stats = useRssStats(eligible("rss"));
  const reddit = useQuery({
    queryKey: ["settings", "feed", "reddit", prefs?.subreddits],
    enabled: eligible("reddit") && Boolean(prefs?.subreddits.length),
    queryFn: () => api.get<RedditPost[]>("/news/reddit?limit=30"),
    staleTime: 10 * 60_000,
    retry: 1,
  });
  const hn = useQuery({
    queryKey: ["settings", "feed", "hn"],
    enabled: eligible("hn"),
    queryFn: () => api.get<HnStory[]>("/news/hacker-news?limit=30"),
    staleTime: 15 * 60_000,
    retry: 1,
  });
  const gh = useQuery({
    queryKey: ["settings", "feed", "gh"],
    enabled: eligible("gh"),
    queryFn: () => api.get<Repo[]>("/news/github-trending?limit=30"),
    staleTime: 6 * 3600_000,
    retry: 1,
  });
  const hf = useQuery({
    queryKey: ["settings", "feed", "hf", options.date ?? "latest"],
    enabled: eligible("hf"),
    queryFn: () => api.get<Paper[]>(`/news/huggingface-papers${qs({ limit: 30, date: options.date || undefined })}`),
    staleTime: 24 * 3600_000,
    retry: 1,
  });
  const rssCount = new Map<string, number>();
  const rssItems = (rss.data ?? []).filter((item) => {
    if (bundle?.feed_ids.length && !bundle.feed_ids.includes(item.feed_id)) return false;
    const count = rssCount.get(item.feed_id) ?? 0;
    rssCount.set(item.feed_id, count + 1);
    return count < (filter === "rss" ? 15 : 5);
  });
  const groups: Record<FeedOrigin, StreamItem[]> = {
    rss: rssItems.map((i) => ({
      key: `rss-${i.id}`,
      entityId: i.id,
      savedBookmarkId: i.saved_bookmark_id ?? undefined,
      feedId: i.feed_id,
      origin: "rss",
      title: i.title,
      href: null,
      canonicalUrl: i.url,
      source: i.feed_title,
      subtitle: i.summary,
      host: i.url ? hostOf(i.url) : null,
      score: null,
      scoreIcon: null,
      commentsUrl: null,
      at: Date.parse(i.published_at || i.fetched_at),
      unread: !i.read_at,
    })),
    reddit: (reddit.data ?? []).map((i) => ({
      key: `reddit-${i.id}`,
      origin: "reddit",
      title: i.title,
      href: i.url,
      source: i.subreddit ? `r/${i.subreddit}` : "Reddit",
      subtitle: null,
      host: hostOf(i.url),
      score: null,
      scoreIcon: null,
      commentsUrl: i.comments_url,
      at: i.published_at ? Date.parse(i.published_at) : 0,
      unread: false,
    })),
    hn: (hn.data ?? []).map((i) => ({
      key: `hn-${i.objectID}`,
      origin: "hn",
      title: i.title,
      href: i.url || hnItem + i.objectID,
      source: "Hacker News",
      subtitle: null,
      host: i.url ? hostOf(i.url) : null,
      score: i.points,
      scoreIcon: "points",
      commentsUrl: hnItem + i.objectID,
      commentCount: i.num_comments,
      at: Date.parse(i.created_at),
      unread: false,
    })),
    gh: (gh.data ?? []).map((i) => ({
      key: `gh-${i.full_name}`,
      origin: "gh",
      title: i.full_name,
      href: i.html_url,
      source: i.language || "GitHub",
      subtitle: i.description,
      host: "github.com",
      score: i.stargazers_count,
      scoreIcon: "stars",
      commentsUrl: null,
      at: Date.parse(i.created_at),
      unread: false,
    })),
    hf: (hf.data ?? []).map((i) => ({
      key: `hf-${i.id}`,
      origin: "hf",
      title: i.title,
      href: i.url,
      paperId: i.id,
      source: "Hugging Face Papers",
      subtitle: i.summary,
      authors: i.authors,
      arxivUrl: i.arxiv_url,
      featuredAt: i.featured_at,
      score: i.upvotes,
      scoreIcon: "points",
      host: "huggingface.co",
      commentsUrl: i.url,
      at: i.published_at ? Date.parse(i.published_at) : 0,
      unread: false,
    })),
  };
  const queries = { rss, reddit, hn, gh, hf };
  const sources = FEED_FILTERS.filter(
    (source): source is { id: FeedOrigin; label: string } => source.id !== "all" && eligible(source.id),
  ).map((source) => ({
    origin: source.id,
    label: source.label,
    failed: queries[source.id].isError,
    retry: () => void queries[source.id].refetch(),
  }));
  const all = composeFeed(
    sources.map((source) =>
      groups[source.origin].map((item) => ({
        ...item,
        href: safeReadingUrl(item.href),
        canonicalUrl: safeReadingUrl(item.canonicalUrl),
        commentsUrl: safeReadingUrl(item.commentsUrl),
      })),
    ),
    200,
  );
  return {
    filter,
    items: all.slice(0, options.limit ?? 15),
    sources,
    failures: sources.filter((source) => source.failed),
    loading: experience.isLoading || sources.some((source) => queries[source.origin].isLoading),
    unread: eligible("rss") ? (stats.data?.unread ?? null) : null,
    hasMore: all.length > (options.limit ?? 15),
    preferencesError: experience.isError,
    retryPreferences: () => void experience.refetch(),
    available: FEED_FILTERS.filter(
      (option) =>
        option.id === "all" ||
        (prefs && (option.id === "rss" ? prefs.rss_enabled : prefs.providers.includes(option.id))),
    ),
  };
}
