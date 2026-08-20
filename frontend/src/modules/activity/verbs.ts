/** Event verb -> insan diline cevirici. Yeni modul kendi verb'lerini buraya ekler. */
export const VERB_LABELS: Record<string, string> = {
  "bookmark.saved": "Bookmark kaydedildi",
  "bookmark.moved": "Bookmark tasindi",
  "bookmark.read": "Bookmark okundu",
  "bookmark.favorited": "Favori degisti",
  "bookmark.deleted": "Bookmark silindi",
  "rss.feed_added": "Feed eklendi",
  "rss.feed_removed": "Feed silindi",
  "rss.items_added": "Yeni RSS yazilari",
  "rss.item_read": "RSS yazisi okundu",
  "rss.item_saved": "RSS yazisi kaydedildi",
  "rss.marked_all_read": "Tumu okundu isaretlendi",
  "rss.feed_failed": "Feed hata verdi",
  "rss.feed_disabled": "Feed kapatildi",
  "rss.pruned": "Eski yazilar temizlendi",
  "source.stalled": "Kaynak sessizlesti",
};

export const ALERT_VERBS = new Set([
  "source.stalled",
  "rss.feed_failed",
  "rss.feed_disabled",
]);

export function describe(verb: string, payload: Record<string, unknown>): string {
  const label = VERB_LABELS[verb] ?? verb;
  const move = payload.to ? `${payload.from ?? "?"} → ${payload.to}` : undefined;
  const detail =
    (payload.message as string | undefined) ??
    move ??
    (payload.title as string | undefined) ??
    (payload.url as string | undefined) ??
    "";
  const count = payload.count ? ` (${payload.count})` : "";
  return `${label}${count}${detail ? ` — ${detail}` : ""}`;
}
