import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useVirtualizer } from "@/lib/useVirtual";
import { ChevronDown, RefreshCw, Settings2, Trash2 } from "lucide-react";
import { api, qs } from "@/core/api";
import {
  Button,
  Chip,
  Empty,
  FileInput,
  Input,
  PageFrame,
  Surface,
  cx,
  relativeTime,
  useToast,
  SkeletonRows,
} from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { useOnline } from "@/lib/hooks";
import { SectionFallback, dataState } from "@/core/DataState";
import { useRssStats } from "@/core/runtimeQueries";
import { feedStateView, type StatusTone } from "@/core/sourceStatus";
import { navigate } from "@/app/router";
import type { Bookmark, Collection, Feed, FeedItem } from "@/core/types";
import { appDayUtc } from "@/lib/date";
import { RssReadingPane } from "./RssReadingPane";

type SmartView = "unread" | "today" | "saved" | "all";

const SMART_LABELS: Record<SmartView, string> = {
  unread: "Tüm Okunmamışlar",
  today: "Bugün",
  saved: "Kaydedilenler",
  all: "Tümü",
};

const SMART_ORDER: SmartView[] = ["unread", "today", "saved", "all"];

function todayIso(): string {
  // App gununun UTC-projekte temsili (Faz 14) -- tarayici tz'den bagimsiz.
  return appDayUtc(new Date()).toISOString();
}

/* ── Besleme ekle / OPML ─────────────────────────────────────────────── */

function AddFeed() {
  const [url, setUrl] = useState("");
  const [category, setCategory] = useState("");
  const online = useOnline();
  const fileRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const add = useMutation({
    mutationFn: () => api.post("/rss/feeds", { url: url.trim(), category: category.trim() || null }),
    onSuccess: () => {
      setUrl("");
      invalidateAfter("rss.write");
    },
    onError: (error: Error) => toast.push(`Besleme eklenemedi: ${error.message}`, { tone: "danger" }),
  });

  const importOpml = useMutation({
    mutationFn: (file: File) => api.upload<{ added: number; skipped: number }>("/rss/import", file),
    onSuccess: (result) => {
      invalidateAfter("rss.write");
      // import sonrasi arka plan cekimi worker'i beklemeden yazilari getirir
      toast.push(
        result.added > 0
          ? `${result.added} besleme eklendi, ${result.skipped} zaten vardı. Yazılar çekiliyor…`
          : `${result.skipped} besleme zaten vardı.`,
        { tone: result.added > 0 ? "ok" : "neutral" },
      );
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
        <Input value={url} onChange={setUrl} placeholder="Besleme URL’si" className="w-full" />
        <Input
          value={category}
          onChange={setCategory}
          placeholder="Kategori (AI/LLM, Development...)"
          className="w-full"
        />
        <Button type="submit" variant="primary" disabled={!online || add.isPending}>
          Besleme ekle
        </Button>
      </form>

      <FileInput
        ref={fileRef}
        accept=".opml,.xml,text/xml"
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

/* ── Kenar çubuğu satırları ──────────────────────────────────────────── */

/**
 * Feed avatari: feed logosu varsa imaj, yoksa ya da hata verirse bas harf kutusu.
 * Imaj istekleri host tarafinda; harf avatari her durumda calisir.
 */
function FeedAvatar({ feed, size = 16 }: { feed?: Feed | null; size?: number }) {
  // Imaj adaylari: (1) feed logosu, (2) sitenin /favicon.ico'su, (3) harf avatari.
  const [failed, setFailed] = useState<Set<string>>(new Set());
  let host: string | null = null;
  if (feed?.url) {
    try {
      host = new URL(feed.url).hostname;
    } catch {
      host = null;
    }
  }
  const candidates = [feed?.favicon_url, host ? `https://${host}/favicon.ico` : null].filter((v): v is string =>
    Boolean(v),
  );
  const src = candidates.find((c) => !failed.has(c));

  if (src) {
    return (
      <img
        src={src}
        alt=""
        width={size}
        height={size}
        loading="lazy"
        onError={() => setFailed((prev) => new Set(prev).add(src as string))}
        className="shrink-0 rounded-sm bg-surface-sunken"
        style={{ width: size, height: size }}
      />
    );
  }
  const initial = ((feed?.title ?? "?").trim().charAt(0) || "?").toUpperCase();
  return (
    <span
      className="flex shrink-0 select-none items-center justify-center rounded-sm bg-surface-sunken text-secondary"
      style={{ width: size, height: size }}
    >
      <span style={{ fontSize: Math.max(9, Math.round(size * 0.62)) }}>{initial}</span>
    </span>
  );
}

/** Durum tonu -> durum led'i rengi (etiketler/tonlar `@/core/sourceStatus`'tan). */
const LED_CLASS: Record<StatusTone, string> = {
  ok: "bg-ok",
  warn: "bg-warn",
  danger: "bg-danger",
  accent: "bg-accent",
  neutral: "bg-icon",
};

function FeedRow({
  feed,
  selected,
  onSelect,
  onRefresh,
  onRemove,
}: {
  feed: Feed;
  selected: boolean;
  onSelect: () => void;
  onRefresh: () => void;
  onRemove: () => void;
}) {
  const online = useOnline();
  // Durum sozlugu tek kaynaktan: bilerek kapatilan besleme "kapali"dir, bozuk degil.
  const view = feedStateView(feed);
  return (
    <li className="group flex items-center gap-1">
      <button
        onClick={onSelect}
        title={feed.url}
        className={cx(
          "flex min-w-0 flex-1 items-center gap-1.5 rounded px-2 py-1 text-left text-body transition",
          selected ? "bg-surface-sunken text-primary" : "text-secondary hover:bg-surface-hover",
        )}
      >
        <FeedAvatar feed={feed} />
        <span className="truncate">{feed.title}</span>
        {feed.unread > 0 && <span className="numeral ml-auto shrink-0 text-meta text-accent">{feed.unread}</span>}
        <span
          role="img"
          aria-label={view.label}
          title={view.label}
          className={cx("ml-auto h-1.5 w-1.5 shrink-0 rounded-full", LED_CLASS[view.tone])}
        />
      </button>
      {/* Hover aksiyonlari — fareyle gelince gorunur */}
      <span className="hidden shrink-0 items-center gap-0.5 group-hover:flex">
        <button
          type="button"
          disabled={!online}
          title="Şimdi çek"
          onClick={onRefresh}
          className="flex h-6 w-6 items-center justify-center rounded text-muted hover:bg-surface-hover hover:text-primary disabled:cursor-not-allowed disabled:opacity-40"
        >
          <RefreshCw size={13} />
        </button>
        <button
          type="button"
          disabled={!online}
          title="Beslemeyi sil"
          onClick={onRemove}
          className="flex h-6 w-6 items-center justify-center rounded text-muted hover:bg-danger-surface hover:text-danger disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Trash2 size={13} />
        </button>
      </span>
    </li>
  );
}

/* ── Liste satırı ────────────────────────────────────────────────────── */

function ItemRow({
  item,
  feed,
  selected,
  onOpen,
}: {
  item: FeedItem;
  feed?: Feed;
  selected: boolean;
  onOpen: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className={cx(
          "w-full px-3 py-2 text-left transition",
          selected ? "bg-accent-surface" : "hover:bg-surface-hover",
        )}
      >
        <div className={cx("truncate text-body", item.read_at ? "font-normal text-muted" : "font-medium text-primary")}>
          {item.title}
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-meta text-muted">
          <FeedAvatar feed={feed} size={14} />
          <span className="max-w-[180px] truncate">{item.feed_title}</span>
          {item.published_at && <span>· {relativeTime(item.published_at)}</span>}
          {item.saved_bookmark_id && <Chip tone="ok">kayıtlı</Chip>}
        </div>
      </button>
    </li>
  );
}

/* ── Sayfa ───────────────────────────────────────────────────────────── */

export function RssPage() {
  const online = useOnline();
  const toast = useToast();

  const [smart, setSmart] = useState<SmartView>("unread");
  const [feedId, setFeedId] = useState<string | null>(null);
  const [categorySel, setCategorySel] = useState<string | null>(null);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [saveCollection, setSaveCollection] = useState<Collection>("read_later");
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [showAdd, setShowAdd] = useState(false);

  const feedsQuery = useQuery({
    queryKey: ["feeds"],
    queryFn: () => api.get<Feed[]>("/rss/feeds"),
  });
  const feeds = feedsQuery.data ?? [];
  const feedsState = dataState(feedsQuery);

  // Paylasilan uç: anahtar/aralik `core/runtimeQueries`'te tek yerde durur (§78).
  const { data: stats } = useRssStats();

  const itemParams: Record<string, string | number | boolean | undefined | null> = { limit: 100 };
  if (feedId) {
    itemParams.feed_id = feedId;
    if (unreadOnly) itemParams.unread_only = true;
  } else if (categorySel) {
    itemParams.category = categorySel;
    if (unreadOnly) itemParams.unread_only = true;
  } else if (smart === "unread") {
    itemParams.unread_only = true;
  } else if (smart === "all" && unreadOnly) {
    // "Tümü" gorunumunde okunmamis/açık filtre butonu ise yarar
    itemParams.unread_only = true;
  } else if (smart === "today") {
    itemParams.since = todayIso();
  } else if (smart === "saved") {
    itemParams.saved_only = true;
  }

  const {
    data: items = [],
    isLoading,
    isError: itemsFailed,
    refetch: retryItems,
  } = useQuery({
    queryKey: ["items", itemParams],
    queryFn: () => api.get<FeedItem[]>(`/rss/items${qs(itemParams)}`),
  });

  const parentRef = useRef<HTMLDivElement>(null);
  const feedMap = useMemo(() => new Map(feeds.map((f) => [f.id, f])), [feeds]);

  const rowVirtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 74,
    overscan: 5,
  });

  const { data: detail } = useQuery({
    queryKey: ["rss-item", selectedId],
    queryFn: () => api.get<FeedItem>(`/rss/items/${selectedId}`),
    enabled: Boolean(selectedId),
  });

  const refreshAll = () => invalidateAfter("rss.write");

  const markRead = useMutation({
    mutationFn: ({ id, read }: { id: string; read: boolean }) => api.post(`/rss/items/${id}/read${qs({ read })}`),
    onSuccess: refreshAll,
  });

  const save = useMutation({
    mutationFn: ({ id, collection }: { id: string; collection: string }) =>
      api.post<Bookmark>(`/rss/items/${id}/save`, { collection }),
    onSuccess: (bookmark) => {
      invalidateAfter("rss.write", "bookmark.write");
      toast.push(`"${(bookmark.title || "").slice(0, 40)}" yer imlerine kaydedildi`, {
        tone: "ok",
        action: { label: "Yer iminde aç", run: () => navigate(`/bookmarks?focus=${bookmark.id}`) },
      });
    },
  });

  const readAll = useMutation({
    mutationFn: () =>
      api.post(
        `/rss/read-all${qs({
          feed_id: feedId ?? undefined,
          category: categorySel ?? undefined,
        })}`,
      ),
    onSuccess: refreshAll,
  });

  const refreshAllFeed = useMutation({
    mutationFn: () => api.post("/rss/refresh-all"),
    onSuccess: (result) => {
      invalidateAfter("rss.write");
      toast.push(
        (result as { started: number }).started > 0
          ? `${(result as { started: number }).started} besleme çekiliyor…`
          : "Süresi gelen besleme yok — hepsi taze.",
        { tone: (result as { started: number }).started > 0 ? "neutral" : "ok" },
      );
    },
  });

  const refreshFeed = useMutation({
    mutationFn: (id: string) => api.post(`/rss/feeds/${id}/refresh`),
    onSuccess: refreshAll,
  });

  const removeFeed = useMutation({
    mutationFn: (id: string) => api.del(`/rss/feeds/${id}`),
    onSuccess: () => {
      if (feedId) setFeedId(null);
      invalidateAfter("rss.write");
    },
  });

  function openItem(item: FeedItem) {
    setSelectedId(item.id);
    setSaveCollection("read_later");
    if (!item.read_at) markRead.mutate({ id: item.id, read: true });
  }

  function selectView(nextSmart: SmartView) {
    setSmart(nextSmart);
    setFeedId(null);
    setCategorySel(null);
    setSelectedId(null);
  }

  function selectFeed(id: string | null) {
    setFeedId(id);
    setCategorySel(null);
    setSelectedId(null);
    setUnreadOnly(false);
  }

  /** Klasor (kategori) secimi: o kategorideki TUM feed'lerin yazilari gelir. */
  function selectCategory(name: string) {
    setCategorySel(name);
    setFeedId(null);
    setSelectedId(null);
  }

  const index = items.findIndex((i) => i.id === selectedId);
  const hasPrev = index > 0;
  const hasNext = index >= 0 && index < items.length - 1;

  function step(delta: number) {
    const target = items[index + delta];
    if (target) openItem(target);
  }

  // Sayfa seviyesinde guvenilir J/K klavye gezintisi: kullanici listeden
  // baska yere tiklasa bile (input/textarea haric) kisayollar kesilmez.
  useEffect(() => {
    if (items.length === 0) return;
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) {
        return;
      }
      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        step(1);
        return;
      }
      if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        step(-1);
        return;
      }
      if (e.key === "u" || e.key === "Enter") {
        e.preventDefault();
        const it = items[index >= 0 ? index : 0];
        if (it) markRead.mutate({ id: it.id, read: !it.read_at });
        return;
      }
      if (e.key === "s" || e.key === "S") {
        e.preventDefault();
        const it = items[index >= 0 ? index : 0];
        if (it && !it.saved_bookmark_id) save.mutate({ id: it.id, collection: "read_later" });
        return;
      }
      if (e.key === "J") {
        e.preventDefault();
        const next = items.find((i, idx) => idx > index && !i.read_at) ?? items.find((i) => !i.read_at);
        if (next) openItem(next);
        return;
      }
      if (e.key === "Escape") {
        setSelectedId(null);
        return;
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [items, index, markRead, save, openItem, step]);

  const selectedFeed = feeds.find((f) => f.id === feedId);
  const title = feedId ? (selectedFeed?.title ?? "RSS") : (categorySel ?? SMART_LABELS[smart]);

  function toggleCategory(key: string) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  const grouped = feeds.reduce<Record<string, Feed[]>>((acc, feed) => {
    const key = feed.category || "Kategorisiz";
    (acc[key] ??= []).push(feed);
    return acc;
  }, {});

  const folderKeys = Object.keys(grouped);
  const allClosed = folderKeys.length > 0 && folderKeys.every((k) => collapsed.has(k));

  /** Tek buton: hepsi acikken hepsini daralt, degilse hepsini genislet. */
  function toggleAllFolders() {
    setCollapsed(allClosed ? new Set() : new Set(folderKeys));
  }

  async function confirmRemove(feed: Feed) {
    const ok = await confirmDialog({
      title: "Besleme silinsin mi?",
      body: (
        <>
          <strong className="font-medium text-primary">{feed.title}</strong> ve ona bağlı okunmamış yazılar listeden
          kalkar. Bu işlem geri alınamaz.
        </>
      ),
      confirmLabel: "Sil",
      tone: "danger",
    });
    if (ok) removeFeed.mutate(feed.id);
  }

  return (
    <PageFrame className="flex min-h-workspace-body flex-col py-3">
      <Surface className="grid min-h-0 flex-1 overflow-hidden md:grid-cols-workspace-rail xl:grid-cols-workspace-reader">
        {/* ── Sol: akıllı görünümler + beslemeler ── */}
        <aside className="flex max-h-[380px] min-w-0 flex-col overflow-y-auto border-b border-subtle p-3 md:max-h-[560px] md:border-b-0 md:border-r xl:max-h-none">
          <div className="mb-2 flex items-center justify-between px-1">
            <span className="label-caps">Görünümler</span>
            <button
              type="button"
              disabled={!online}
              onClick={() => refreshAllFeed.mutate()}
              title="Süresi gelen tüm beslemeleri çek"
              className="flex h-6 items-center gap-1 rounded px-1.5 text-meta text-muted hover:bg-surface-hover hover:text-primary disabled:cursor-not-allowed disabled:opacity-40"
            >
              <RefreshCw size={12} /> Tümünü tazele
            </button>
          </div>
          <ul className="space-y-0.5">
            {SMART_ORDER.map((v) => {
              const count =
                v === "unread"
                  ? stats?.unread
                  : v === "today"
                    ? stats?.today
                    : v === "saved"
                      ? stats?.saved
                      : undefined;
              return (
                <li key={v}>
                  <button
                    type="button"
                    onClick={() => selectView(v)}
                    className={cx(
                      "flex w-full items-center gap-2 rounded px-2 py-1 text-left text-body transition",
                      !feedId && !categorySel && smart === v
                        ? "bg-surface-sunken font-medium text-primary"
                        : "text-secondary hover:bg-surface-hover",
                    )}
                  >
                    <span className="truncate">{SMART_LABELS[v]}</span>
                    {count !== undefined && (
                      <span
                        className={cx(
                          "numeral ml-auto text-meta",
                          !feedId && !categorySel && smart === v ? "text-accent" : "text-muted",
                        )}
                      >
                        {count}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="mt-3 mb-1 flex items-center justify-between border-b border-subtle pb-2">
            <span className="label-caps">Klasörler</span>
            {folderKeys.length > 0 && (
              <button
                type="button"
                onClick={toggleAllFolders}
                title={allClosed ? "Tüm klasörleri aç" : "Tüm klasörleri daralt"}
                className="text-meta text-muted transition hover:text-primary"
              >
                {allClosed ? "Tümünü genişlet" : "Tümünü daralt"}
              </button>
            )}
          </div>

          <div className="space-y-3">
            {Object.entries(grouped).map(([category, group]) => {
              const unreadSum = group.reduce((acc, f) => acc + f.unread, 0);
              const key = category;
              const isClosed = collapsed.has(key);
              return (
                <div key={key}>
                  <div className="flex items-center gap-0.5">
                    <button
                      type="button"
                      onClick={() => toggleCategory(key)}
                      title={isClosed ? "Klasörü aç" : "Klasörü kapat"}
                      aria-expanded={!isClosed}
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded text-secondary hover:bg-surface-hover hover:text-primary"
                    >
                      <ChevronDown
                        size={16}
                        className={cx("transition-transform duration-150", isClosed && "-rotate-90")}
                      />
                    </button>
                    <button
                      type="button"
                      onClick={() => selectCategory(key)}
                      title="Klasördeki tüm yazıları göster"
                      className={cx(
                        "flex min-w-0 flex-1 items-center gap-1.5 rounded px-1.5 py-0.5 text-left text-meta uppercase tracking-wide transition",
                        categorySel === key
                          ? "bg-surface-sunken font-medium text-primary"
                          : "text-muted hover:text-primary",
                      )}
                    >
                      <span className="truncate">{category}</span>
                      {unreadSum > 0 && <span className="numeral ml-auto text-meta text-accent">{unreadSum}</span>}
                    </button>
                  </div>
                  {!isClosed && (
                    <ul className="mt-0.5 space-y-0.5">
                      {group.map((feed) => (
                        <FeedRow
                          key={feed.id}
                          feed={feed}
                          selected={feedId === feed.id}
                          onSelect={() => selectFeed(feed.id)}
                          onRefresh={() => refreshFeed.mutate(feed.id)}
                          onRemove={() => confirmRemove(feed)}
                        />
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>

          {feedsState !== "ready" && (
            /* Yukleniyor/hata/bos ayri soylenir: sorgu hatasi "besleme yok" DEGILDIR. */
            <SectionFallback
              state={feedsState}
              what="Besleme listesi"
              onRetry={() => void feedsQuery.refetch()}
              emptyLabel="Henüz besleme yok. Aşağıdan URL ekle ya da OPML dosyanı içeri aktar."
            />
          )}

          <div className="mt-4 border-t border-subtle pt-3">
            <button
              type="button"
              onClick={() => setShowAdd((v) => !v)}
              aria-expanded={showAdd}
              className="flex h-8 w-full items-center justify-center gap-2 rounded-control border border-subtle bg-surface text-meta text-secondary transition hover:bg-surface-hover hover:text-primary"
            >
              <Settings2 size={14} />
              {showAdd ? "Ekleme formunu kapat" : "Besleme ekle / OPML"}
            </button>
            {showAdd && (
              <div className="mt-2">
                <AddFeed />
              </div>
            )}
          </div>
        </aside>

        {/* ── Orta: yazı listesi ── */}
        <section className="flex min-h-[420px] min-w-0 flex-col border-b border-subtle md:border-b-0 xl:border-r">
          <div className="border-b border-subtle px-4 py-2.5">
            <div className="flex items-center gap-2">
              <h2 className="min-w-0 flex-1 truncate  text-heading text-primary">{title}</h2>
              {(feedId || categorySel || smart === "all") && (
                <Button
                  size="sm"
                  variant={unreadOnly ? "primary" : "ghost"}
                  onClick={() => setUnreadOnly((v) => !v)}
                  title="Sadece okunmamışlar"
                >
                  {unreadOnly ? "okunmamış" : "hepsi"}
                </Button>
              )}
              <Button
                size="sm"
                disabled={!online || items.length === 0}
                onClick={() => readAll.mutate()}
                title="Listedekileri okundu işaretle"
              >
                okundu
              </Button>
            </div>
            {feedId && selectedFeed?.last_fetched_at == null && (
              <p className="mt-1.5 text-meta text-warn">
                Bu besleme henüz çekilmedi — satırdaki ⟳ veya "Tümünü tazele" ile getir.
              </p>
            )}
            <p className="mt-1 text-meta text-muted">{items.length} yazı</p>
          </div>

          <div ref={parentRef} className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
            {isLoading ? (
              <SkeletonRows rows={5} className="h-9" />
            ) : itemsFailed ? (
              /* Sorgu hatasi BOSLUK degildir: "yazi yok" demek yanlis olurdu. */
              <SectionFallback state="error" what="Yazılar" onRetry={() => void retryItems()} />
            ) : items.length === 0 ? (
              <Empty>
                {smart === "unread" && !feedId ? "Okunacak yazı yok — hepsi yakalandı." : "Bu görünümde yazı yok."}
              </Empty>
            ) : (
              <div
                style={{
                  height: `${rowVirtualizer.getTotalSize()}px`,
                  width: "100%",
                  position: "relative",
                }}
              >
                {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                  const item = items[virtualRow.index];
                  return (
                    <div
                      key={item.id}
                      data-index={virtualRow.index}
                      ref={rowVirtualizer.measureElement}
                      style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        width: "100%",
                        transform: `translateY(${virtualRow.start}px)`,
                      }}
                    >
                      <ItemRow
                        item={item}
                        feed={feedMap.get(item.feed_id)}
                        selected={selectedId === item.id}
                        onOpen={() => openItem(item)}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </section>

        {/* ── Sağ: okuma bölmesi ── */}
        <section className="flex min-h-[520px] min-w-0 flex-col border-t border-subtle md:col-span-2 xl:col-span-1 xl:border-t-0">
          <RssReadingPane
            detail={detail}
            online={online}
            saveCollection={saveCollection}
            onSaveCollection={setSaveCollection}
            onToggleRead={() => {
              if (detail?.id) markRead.mutate({ id: detail.id, read: !detail.read_at });
            }}
            onSave={() => {
              if (detail?.id) save.mutate({ id: detail.id, collection: saveCollection });
            }}
            onOpenBookmark={() => {
              if (detail?.saved_bookmark_id) navigate(`/bookmarks?focus=${detail.saved_bookmark_id}`);
            }}
            onPrev={() => step(-1)}
            onNext={() => step(1)}
            hasPrev={hasPrev}
            hasNext={hasNext}
          />
        </section>
      </Surface>
    </PageFrame>
  );
}
