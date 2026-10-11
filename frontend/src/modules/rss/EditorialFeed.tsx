import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { BookmarkPlus, ExternalLink, Star } from "lucide-react";
import { api } from "@/core/api";
import { Button, cx, relativeTime } from "@/core/ui";
import { invalidateAfter } from "@/core/invalidation";
import { entityRoute } from "@/core/entityRegistry";
import { sourceInfo } from "@/core/onboarding/catalog";
import { technologyChip } from "@/core/FeedStreamList";
import type { StreamItem } from "@/core/feedStream";
import { BookmarkLearningAttach } from "@/modules/bookmarks/BookmarkLearningAttach";
import { useOnline } from "@/lib/hooks";
import type { components } from "@/generated/api-schema";
export function EditorialFeed({ items }: { items: StreamItem[] }) {
  return (
    <div className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {items.map((item, index) => (
        <ReadingCard key={item.key} item={item} featured={index === 0} />
      ))}
    </div>
  );
}
function ReadingCard({ item, featured }: { item: StreamItem; featured: boolean }) {
  const info = sourceInfo(item.origin);
  const Icon = info.icon;
  const url = item.canonicalUrl || item.href;
  const uuid = useRef(crypto.randomUUID());
  const [bookmark, setBookmark] = useState<string | null>(item.savedBookmarkId ?? null);
  const online = useOnline();
  const save = useMutation({
    mutationFn: async () => {
      if (item.origin === "rss" && item.entityId) {
        const saved = await api.post<components["schemas"]["BookmarkOut"]>(`/rss/items/${item.entityId}/save`, {
          collection: "read_later",
        });
        return saved.id;
      }
      const saved = await api.post<components["schemas"]["CaptureResult"]>("/capture", {
        client_uuid: uuid.current,
        url,
        title: item.title,
        description: item.subtitle,
        author: item.authors?.join(", "),
        source: "feed:" + item.origin,
        collection: "read_later",
      });
      return saved.existing_id || saved.id;
    },
    onSuccess: (id) => {
      setBookmark(id);
      if (item.origin === "rss") invalidateAfter("rss.write");
      invalidateAfter("bookmark.write");
    },
  });
  const href = item.entityId ? "#" + entityRoute("feed_item", item.entityId) : item.href;
  return (
    <article
      className={cx(
        "group flex min-w-0 flex-col rounded-card border border-subtle bg-surface p-4 sm:p-5",
        featured && "md:col-span-2 bg-surface-sunken",
      )}
    >
      <div className="mb-3 flex items-center gap-2 text-meta text-secondary">
        <Icon size={16} className={info.skin} />
        <span>{item.origin === "gh" ? "GitHub · Yeni ve Popüler" : item.source}</span>
        <span className="ml-auto text-micro text-muted">
          {item.origin === "hf" ? "Makale" : item.origin === "gh" ? "Depo" : "Yazı"}
        </span>
      </div>
      <h2 className={cx("font-serif font-medium leading-snug text-primary", featured ? "text-title" : "text-heading")}>
        <a
          href={href || undefined}
          target={item.entityId ? undefined : "_blank"}
          rel="noreferrer"
          className="hover:text-accent"
        >
          {item.title}
        </a>
      </h2>
      {item.subtitle && (
        <p className={cx("mt-3 text-body text-secondary", featured ? "line-clamp-4" : "line-clamp-3")}>
          {item.subtitle.replace(/<[^>]*>/g, " ")}
        </p>
      )}
      {item.authors?.length ? (
        <p className="mt-3 line-clamp-2 text-meta text-muted">{item.authors.join(", ")}</p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-meta text-muted">
        {item.origin === "gh" && (
          <span className={cx("rounded-control border px-2", technologyChip(item.source))}>{item.source}</span>
        )}
        {item.host && <span>{item.host}</span>}
        {item.at > 0 && (
          <span>
            {item.origin === "hf" ? "Yayın · " : ""}
            {relativeTime(new Date(item.at).toISOString())}
          </span>
        )}
        {item.featuredAt && <span>Seçki · {item.featuredAt.slice(0, 10)}</span>}
        {item.score !== null && (
          <span className="inline-flex items-center gap-1">
            {item.scoreIcon === "stars" && <Star size={12} />} {item.score}{" "}
            {item.origin === "hf" ? "oy" : item.scoreIcon === "stars" ? "yıldız" : "puan"}
          </span>
        )}
      </div>
      {item.commentCount != null && <p className="mt-2 text-meta text-muted">{item.commentCount} yorum</p>}
      {item.origin === "rss" && <p className="mt-2 text-meta text-muted">{item.unread ? "Okunmadı" : "Okundu"}</p>}
      <div className="mt-auto flex flex-wrap items-center gap-2 pt-4">
        <a
          href={href || undefined}
          target={item.entityId ? undefined : "_blank"}
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-meta text-accent"
        >
          {item.entityId ? "Oku" : "Kaynağı aç"}
          <ExternalLink size={12} />
        </a>
        {item.arxivUrl && (
          <a href={item.arxivUrl} target="_blank" rel="noreferrer" className="text-meta text-accent">
            arXiv
          </a>
        )}
        {item.commentsUrl && item.commentsUrl !== item.href && (
          <a href={item.commentsUrl} target="_blank" rel="noreferrer" className="text-meta text-secondary">
            Tartışma
          </a>
        )}
        <span className="flex-1" />
        {bookmark ? (
          <a href={"#" + entityRoute("bookmark", bookmark)} className="text-meta text-accent">
            Kayıtlı · Oku
          </a>
        ) : (
          <Button size="sm" disabled={!online || !url || save.isPending} onClick={() => save.mutate()}>
            <BookmarkPlus size={14} />
            {save.isPending ? "Kaydediliyor…" : "Kaydet"}
          </Button>
        )}
      </div>
      {save.isError && (
        <p role="alert" className="mt-2 text-meta text-danger">
          Kaydedilemedi. Yeniden deneyebilirsin.
        </p>
      )}
      {bookmark && item.origin === "hf" && <BookmarkLearningAttach bookmarkId={bookmark} />}
    </article>
  );
}
