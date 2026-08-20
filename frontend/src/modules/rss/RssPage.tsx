import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Badge, Button, Empty, Panel, cx, hostOf, relativeTime } from "@/core/ui";
import { useInvalidate, useOnline } from "@/lib/hooks";
import { useHashRoute } from "@/app/router";
import type { Feed, FeedItem } from "@/core/types";

function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function AddFeed() {
  const [url, setUrl] = useState("");
  const [category, setCategory] = useState("");
  const online = useOnline();
  const invalidate = useInvalidate();
  const fileRef = useRef<HTMLInputElement>(null);

  const add = useMutation({
    mutationFn: () =>
      api.post("/rss/feeds", { url: url.trim(), category: category.trim() || null }),
    onSuccess: () => {
      setUrl("");
      invalidate("feeds", "rss-stats", "activity");
    },
    onError: (error: Error) => alert(`Feed eklenemedi: ${error.message}`),
  });

  const importOpml = useMutation({
    mutationFn: (file: File) =>
      api.upload<{ added: number; skipped: number }>("/rss/import", file),
    onSuccess: (result) => {
      invalidate("feeds", "rss-stats", "activity");
      alert(`${result.added} feed eklendi, ${result.skipped} zaten vardi.`);
    },
  });

  return (
    <div className="space-y-2">
      <form
        className="space-y-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (url.trim()) add.mutate();
        }}
      >
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Feed URL"
          className="w-full rounded border border-neutral-800 bg-neutral-900 px-2 py-1.5 text-sm outline-none focus:border-neutral-600"
        />
        <input
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          placeholder="Kategori (AI/LLM, Development...)"
          className="w-full rounded border border-neutral-800 bg-neutral-900 px-2 py-1.5 text-sm outline-none focus:border-neutral-600"
        />
        <Button type="submit" variant="primary" disabled={!online || add.isPending}>
          Feed ekle
        </Button>
      </form>

      <input
        ref={fileRef}
        type="file"
        accept=".opml,.xml,text/xml"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) importOpml.mutate(file);
          e.target.value = "";
        }}
      />
      <Button disabled={!online || importOpml.isPending} onClick={() => fileRef.current?.click()}>
        OPML iceri aktar
      </Button>
    </div>
  );
}

function FeedRow({
  feed, selected, onSelect,
}: {
  feed: Feed;
  selected: boolean;
  onSelect: () => void;
}) {
  const online = useOnline();
  const invalidate = useInvalidate();
  const refresh = useMutation({
    mutationFn: () => api.post(`/rss/feeds/${feed.id}/refresh`),
    onSuccess: () => invalidate("feeds", "items", "rss-stats", "activity"),
  });
  const remove = useMutation({
    mutationFn: () => api.del(`/rss/feeds/${feed.id}`),
    onSuccess: () => invalidate("feeds", "items", "rss-stats"),
  });

  return (
    <li className="group flex items-center gap-1">
      <button
        onClick={onSelect}
        className={cx(
          "min-w-0 flex-1 truncate rounded px-2 py-1 text-left text-sm",
          selected ? "bg-neutral-800 text-neutral-100" : "text-neutral-400 hover:bg-neutral-900",
        )}
      >
        {feed.title}
        {feed.unread > 0 && <span className="ml-1 text-[11px] text-sky-400">{feed.unread}</span>}
        {!feed.active && <span className="ml-1 text-[11px] text-red-400">kapali</span>}
      </button>
      <span className="hidden gap-1 group-hover:flex">
        <Button disabled={!online} title="Simdi cek" onClick={() => refresh.mutate()}>
          ⟳
        </Button>
        <Button
          variant="danger"
          disabled={!online}
          onClick={() => confirm(`${feed.title} silinsin mi?`) && remove.mutate()}
        >
          ✕
        </Button>
      </span>
    </li>
  );
}

function ItemRow({ item }: { item: FeedItem }) {
  const online = useOnline();
  const invalidate = useInvalidate();
  const [expanded, setExpanded] = useState(false);
  const refresh = () => invalidate("items", "feeds", "rss-stats", "bookmarks", "activity");

  const read = useMutation({
    mutationFn: (value: boolean) => api.post(`/rss/items/${item.id}/read${qs({ read: value })}`),
    onSuccess: refresh,
  });
  const save = useMutation({
    mutationFn: (collection: string) =>
      api.post(`/rss/items/${item.id}/save`, { collection }),
    onSuccess: refresh,
  });

  return (
    <li
      className={cx(
        "rounded border p-3",
        item.read_at ? "border-neutral-900 bg-transparent" : "border-neutral-800 bg-neutral-900/40",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <button
            onClick={() => setExpanded((v) => !v)}
            className={cx(
              "block w-full truncate text-left text-sm",
              item.read_at ? "text-neutral-500" : "text-neutral-100",
            )}
          >
            {item.title}
          </button>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-neutral-500">
            <span>{item.feed_title}</span>
            {item.url && <span>· {hostOf(item.url)}</span>}
            {item.published_at && <span>· {relativeTime(item.published_at)}</span>}
            {item.author && <span>· {item.author}</span>}
            {item.saved_bookmark_id && <Badge tone="ok">kaydedildi</Badge>}
          </div>
          {expanded && item.summary && (
            <p className="mt-2 text-xs leading-relaxed text-neutral-400">
              {stripHtml(item.summary).slice(0, 900)}
            </p>
          )}
          {expanded && item.url && (
            <a
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-block text-xs text-sky-400 hover:underline"
              onClick={() => !item.read_at && read.mutate(true)}
            >
              Yaziyi ac →
            </a>
          )}
        </div>

        <div className="flex flex-wrap justify-end gap-1">
          <Button disabled={!online} onClick={() => read.mutate(!item.read_at)}>
            {item.read_at ? "okunmadi" : "okundu"}
          </Button>
          <Button
            variant="primary"
            disabled={!online || !!item.saved_bookmark_id}
            title="Read Later'a kaydet"
            onClick={() => save.mutate("read_later")}
          >
            → Read Later
          </Button>
          <Button
            disabled={!online || !!item.saved_bookmark_id}
            title="Learning'e kaydet"
            onClick={() => save.mutate("learning")}
          >
            → Learning
          </Button>
        </div>
      </div>
    </li>
  );
}

export function RssPage() {
  const { params } = useHashRoute();
  const online = useOnline();
  const invalidate = useInvalidate();
  const [feedId, setFeedId] = useState<string | null>(params.get("feed"));
  const [unreadOnly, setUnreadOnly] = useState(true);

  const { data: feeds = [] } = useQuery({
    queryKey: ["feeds"],
    queryFn: () => api.get<Feed[]>("/rss/feeds"),
  });

  const itemQuery = { feed_id: feedId ?? undefined, unread_only: unreadOnly, limit: 100 };
  const { data: items = [], isLoading } = useQuery({
    queryKey: ["items", itemQuery],
    queryFn: () => api.get<FeedItem[]>(`/rss/items${qs(itemQuery)}`),
  });

  const readAll = useMutation({
    mutationFn: () => api.post(`/rss/read-all${qs({ feed_id: feedId ?? undefined })}`),
    onSuccess: () => invalidate("items", "feeds", "rss-stats", "activity"),
  });

  const grouped = feeds.reduce<Record<string, Feed[]>>((acc, feed) => {
    const key = feed.category || "Kategorisiz";
    (acc[key] ??= []).push(feed);
    return acc;
  }, {});

  return (
    <div className="grid gap-4 p-6 lg:grid-cols-[240px_1fr]">
      <aside className="space-y-4">
        <Panel title="Feed'ler">
          <ul className="mb-3 space-y-1">
            <li>
              <button
                onClick={() => setFeedId(null)}
                className={cx(
                  "w-full rounded px-2 py-1 text-left text-sm",
                  !feedId ? "bg-neutral-800 text-neutral-100" : "text-neutral-400 hover:bg-neutral-900",
                )}
              >
                Tumu
              </button>
            </li>
          </ul>
          {Object.entries(grouped).map(([category, group]) => (
            <div key={category} className="mb-3">
              <div className="mb-1 text-[11px] uppercase tracking-wide text-neutral-600">
                {category}
              </div>
              <ul className="space-y-0.5">
                {group.map((feed) => (
                  <FeedRow
                    key={feed.id}
                    feed={feed}
                    selected={feedId === feed.id}
                    onSelect={() => setFeedId(feed.id)}
                  />
                ))}
              </ul>
            </div>
          ))}
          {feeds.length === 0 && <Empty>Feed yok. OPML aktar veya URL ekle.</Empty>}
        </Panel>

        <Panel title="Ekle">
          <AddFeed />
        </Panel>
      </aside>

      <div>
        <header className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-xl font-semibold">
            {feedId ? feeds.find((f) => f.id === feedId)?.title ?? "RSS" : "RSS Reader"}
          </h1>
          <div className="flex items-center gap-2">
            <Button
              variant={unreadOnly ? "primary" : "ghost"}
              onClick={() => setUnreadOnly((v) => !v)}
            >
              {unreadOnly ? "sadece okunmamis" : "hepsi"}
            </Button>
            <Button disabled={!online || items.length === 0} onClick={() => readAll.mutate()}>
              tumunu okundu isaretle
            </Button>
          </div>
        </header>

        {isLoading ? (
          <p className="text-sm text-neutral-500">Yukleniyor...</p>
        ) : items.length === 0 ? (
          <Empty>Okunacak yeni bir sey yok.</Empty>
        ) : (
          <ul className="space-y-2">
            {items.map((item) => (
              <ItemRow key={item.id} item={item} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
