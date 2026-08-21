import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Badge, Button, Empty, Panel, cx, hostOf, relativeTime, useToast } from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
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
  const toast = useToast();

  const add = useMutation({
    mutationFn: () =>
      api.post("/rss/feeds", { url: url.trim(), category: category.trim() || null }),
    onSuccess: () => {
      setUrl("");
      invalidate("feeds", "rss-stats", "activity");
    },
    onError: (error: Error) => toast.push(`Besleme eklenemedi: ${error.message}`, { tone: "danger" }),
  });

  const importOpml = useMutation({
    mutationFn: (file: File) =>
      api.upload<{ added: number; skipped: number }>("/rss/import", file),
    onSuccess: (result) => {
      invalidate("feeds", "rss-stats", "activity");
      toast.push(`${result.added} besleme eklendi, ${result.skipped} zaten vardı.`, { tone: "ok" });
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
          placeholder="Besleme URL’si"
          className="w-full rounded border border-subtle bg-surface px-2 py-1.5 text-body outline-none focus:border-accent"
        />
        <input
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          placeholder="Kategori (AI/LLM, Development...)"
          className="w-full rounded border border-subtle bg-surface px-2 py-1.5 text-body outline-none focus:border-accent"
        />
        <Button type="submit" variant="primary" disabled={!online || add.isPending}>
          Besleme ekle
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
        OPML içeri aktar
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
          "min-w-0 flex-1 truncate rounded px-2 py-1 text-left text-body",
          selected ? "bg-surface-sunken text-primary" : "text-secondary hover:bg-surface-hover",
        )}
      >
        {feed.title}
        {feed.unread > 0 && <span className="ml-1 text-meta text-accent">{feed.unread}</span>}
        {!feed.active && <span className="ml-1 text-meta text-danger">kapali</span>}
      </button>
      <span className="hidden gap-1 group-hover:flex">
        <Button disabled={!online} title="Simdi cek" onClick={() => refresh.mutate()}>
          ⟳
        </Button>
        <Button
          variant="danger"
          disabled={!online}
          onClick={async () => {
            const ok = await confirmDialog({
              title: "Besleme silinsin mi?",
              body: <><strong className="font-medium text-primary">{feed.title}</strong> ve ona bağlı okunmamış yazılar listeden kalkar. Bu işlem geri alınamaz.</>,
              confirmLabel: "Sil",
              tone: "danger",
            });
            if (ok) remove.mutate();
          }}
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
        item.read_at ? "border-subtle bg-transparent" : "border-subtle bg-surface",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <button
            onClick={() => setExpanded((v) => !v)}
            className={cx(
              "block w-full truncate text-left text-body",
              item.read_at ? "text-muted" : "text-primary",
            )}
          >
            {item.title}
          </button>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-meta text-muted">
            <span>{item.feed_title}</span>
            {item.url && <span>· {hostOf(item.url)}</span>}
            {item.published_at && <span>· {relativeTime(item.published_at)}</span>}
            {item.author && <span>· {item.author}</span>}
            {item.saved_bookmark_id && <Badge tone="ok">kaydedildi</Badge>}
          </div>
          {expanded && item.summary && (
            <p className="mt-2 text-meta leading-relaxed text-secondary">
              {stripHtml(item.summary).slice(0, 900)}
            </p>
          )}
          {expanded && item.url && (
            <a
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-block text-meta text-accent hover:underline"
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
            title="Okuma listesine kaydet"
            onClick={() => save.mutate("read_later")}
          >
            → Read Later
          </Button>
          <Button
            disabled={!online || !!item.saved_bookmark_id}
            title="Öğrenme’ye kaydet"
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
  const [feedId, setFeedId] = useState<string | null>(params.get("besleme"));
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
        <Panel title="Beslemeler">
          <ul className="mb-3 space-y-1">
            <li>
              <button
                onClick={() => setFeedId(null)}
                className={cx(
                  "w-full rounded px-2 py-1 text-left text-body",
                  !feedId ? "bg-surface-sunken text-primary" : "text-secondary hover:bg-surface-hover",
                )}
              >
                Tümü
              </button>
            </li>
          </ul>
          {Object.entries(grouped).map(([category, group]) => (
            <div key={category} className="mb-3">
              <div className="mb-1 text-meta uppercase tracking-wide text-muted">
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
          {feeds.length === 0 && <Empty>Henüz besleme yok. Yukarıdan URL ekle ya da OPML dosyanı içeri aktar.</Empty>}
        </Panel>

        <Panel title="Ekle">
          <AddFeed />
        </Panel>
      </aside>

      <div>
        <header className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <h2 className="font-serif text-title text-primary">
              {feedId ? feeds.find((f) => f.id === feedId)?.title ?? "RSS" : "Tüm beslemeler"}
            </h2>
            <Button
              variant={unreadOnly ? "primary" : "ghost"}
              onClick={() => setUnreadOnly((v) => !v)}
            >
              {unreadOnly ? "sadece okunmamış" : "hepsi"}
            </Button>
            <Button disabled={!online || items.length === 0} onClick={() => readAll.mutate()}>
              tümünü okundu işaretle
            </Button>
          </div>
        </header>

        {isLoading ? (
          <p className="text-body text-muted">Yükleniyor…</p>
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
