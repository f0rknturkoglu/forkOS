import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ExternalLink, Plus, Search, Star, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { useHashRoute } from "@/app/router";
import { Badge, Button, Empty, Input, Metric, MetricStrip, PageFrame, PageHeader, RowList, Section, Surface, Toolbar, cx, useToast } from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { useInvalidate, useOnline } from "@/lib/hooks";
import type { MediaDetail, MediaItem, MediaPage as MediaPageResponse, MediaStats, MetadataResult } from "@/core/types";
import { SyncProgress } from "@/modules/opportunity/SyncProgress";

type MediaFocusTarget = { focus?: () => void };

type MediaFocusElement = {
  querySelector: (selector: string) => MediaFocusTarget | null;
  scrollIntoView: (options: ScrollIntoViewOptions) => void;
};

type MediaFocusRoot = {
  getElementById: (id: string) => MediaFocusElement | null;
};

export function receiveMediaFocus(
  itemId: string,
  root: MediaFocusRoot = document as unknown as MediaFocusRoot,
): boolean {
  const row = root.getElementById(`media-item-${itemId}`);
  if (!row) return false;
  row.scrollIntoView({ block: "center" });
  row.querySelector('[data-media-focus="true"]')?.focus?.();
  return true;
}

export const MEDIA_REFRESH_KEYS = [
  "media",
  "media-stats",
  "media-dashboard",
  "today-agenda",
  "activity",
] as const;

const KINDS = ["movie", "show", "anime", "manga", "book", "audiobook", "podcast", "music", "game"] as const;
const KIND_LABELS: Record<string, string> = {
  movie: "Film", show: "Dizi", anime: "Anime", manga: "Manga", book: "Kitap",
  audiobook: "Sesli Kitap", podcast: "Podcast", music: "Müzik", game: "Oyun",
};
const STATUSES = ["planned", "in_progress", "paused", "completed", "dropped"] as const;
const STATUS_LABELS: Record<string, string> = {
  planned: "Planlandı", in_progress: "İzleniyor", paused: "Duraklatıldı",
  completed: "Tamamlandı", dropped: "Bırakıldı",
};

function Cover({ url, title, size = "h-24 w-16" }: { url: string | null; title: string; size?: string }) {
  const [broken, setBroken] = useState(false);
  if (url && !broken) {
    return (
      <img src={url} alt="" loading="lazy" onError={() => setBroken(true)}
        className={cx("shrink-0 rounded border border-subtle object-cover", size)} />
    );
  }
  return (
    <div className={cx("flex shrink-0 items-center justify-center rounded border border-subtle bg-surface-sunken text-heading text-secondary", size)}>
      {(title.trim().charAt(0) || "?").toUpperCase()}
    </div>
  );
}

function externalLinks(item: MediaItem, q: string): [string, string][] {
  const meta = item.meta ?? {};
  const links: [string, string][] = [];
  if (meta.source === "anilist" && meta.anilist_id) {
    const base = item.kind === "manga" ? "https://anilist.co/manga/" : "https://anilist.co/anime/";
    links.push(["AniList", base + String(meta.anilist_id)]);
  }
  if (meta.source === "openlibrary" && meta.ol_key) {
    links.push(["OpenLibrary", "https://openlibrary.org" + String(meta.ol_key)]);
  }
  if (meta.source === "tmdb" && meta.tmdb_id) {
    const base = meta.tmdb_type === "tv" ? "https://www.themoviedb.org/tv/" : "https://www.themoviedb.org/movie/";
    links.push(["TMDB", base + String(meta.tmdb_id)]);
  }
  const query = encodeURIComponent(q);
  links.push(["Letterboxd", "https://letterboxd.com/search/" + query + "/"]);
  links.push(["RyM", "https://rateyourmusic.com/search?searchterm=" + query]);
  links.push(["Goodreads", "https://www.goodreads.com/search?q=" + query]);
  return links;
}

const QUICK_SITES: [string, string][] = [
  ["Letterboxd", "https://letterboxd.com/search/"],
  ["RateYourMusic", "https://rateyourmusic.com/search?searchterm="],
  ["AniList", "https://anilist.co/search/anime?search="],
  ["MyAnimeList", "https://myanimelist.net/search/all?q="],
  ["Goodreads", "https://www.goodreads.com/search?q="],
  ["IMDb", "https://www.imdb.com/find/?q="],
];

export function MediaPage() {
  const route = useHashRoute();
  const focusId = route.params.get("focus");
  const online = useOnline();
  const invalidate = useInvalidate();
  const toast = useToast();

  const [kind, setKind] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [searchKind, setSearchKind] = useState("movie");
  const [expanded, setExpanded] = useState<string | null>(() => focusId);

  const query: Record<string, string> = {};
  if (kind) query.kind = kind;
  if (status) query.status = status;
  const { data: page } = useQuery({
    queryKey: ["media", query],
    queryFn: () => api.get<MediaPageResponse>("/media?" + new URLSearchParams(query)),
  });
  const { data: focusedDetail } = useQuery({
    queryKey: ["media-detail", focusId],
    queryFn: () => api.get<MediaDetail>(`/media/${encodeURIComponent(focusId ?? "")}`),
    enabled: Boolean(focusId),
  });
  const listedItems = page?.items ?? [];
  const focusedItem = focusedDetail?.item;
  const items = focusedItem && !listedItems.some((item) => item.id === focusedItem.id)
    ? [focusedItem, ...listedItems]
    : listedItems;
  const { data: stats } = useQuery({
    queryKey: ["media-stats"],
    queryFn: () => api.get<MediaStats>("/media/stats"),
  });
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<Record<string, unknown>>("/settings"),
  });

  const activeTerm = search.trim();

  const { data: results = [], isFetching: searching } = useQuery({
    queryKey: ["media-search", searchKind, activeTerm],
    queryFn: () => api.get<MetadataResult[]>("/media/search?kind=" + searchKind + "&q=" + encodeURIComponent(activeTerm)),
    enabled: activeTerm.length >= 2,
  });

  const refresh = () => invalidate(...MEDIA_REFRESH_KEYS);

  useEffect(() => {
    if (!focusId) return;
    setExpanded(focusId);
    receiveMediaFocus(focusId);
  }, [focusId, focusedItem?.id]);

  const addFromSearch = useMutation({
    mutationFn: (hit: MetadataResult) =>
      api.post<MediaItem>("/media", {
        title: hit.title, kind: searchKind, metadata: hit.metadata,
      }),
    onSuccess: () => { refresh(); toast.push("Kütüphaneye eklendi", { tone: "ok" }); },
    onError: (e: Error) => toast.push("Eklenemedi: " + e.message, { tone: "danger" }),
  });

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      api.patch("/media/" + id, body),
    onSuccess: refresh,
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.del("/media/" + id),
    onSuccess: refresh,
  });

  async function confirmRemove(item: MediaItem) {
    const ok = await confirmDialog({
      title: "Kayıt silinsin mi?",
      body: <><strong className="font-medium text-primary">{item.title}</strong> kütüphaneden kalkar.</>,
      confirmLabel: "Sil", tone: "danger",
    });
    if (ok) remove.mutate(item.id);
  }

  return (
    <PageFrame className="space-y-5">
      {/* ── Özet ── */}
      <PageHeader eyebrow="Takip" title="Medya" />
      <SyncProgress scope="media" compact />
      <MetricStrip className="grid-cols-2 sm:grid-cols-4">
        <Metric label="Toplam" value={stats?.total ?? 0} />
        <Metric label="Devam ediyor" value={stats?.in_progress ?? 0} />
        <Metric label="Tamamlandı" value={stats?.completed ?? 0} />
        <Metric label="Planlandı" value={stats?.planned ?? 0} />
      </MetricStrip>

      {/* ── Ara ve ekle ── */}
      <Section title="Ara ve ekle">
        <Toolbar className="border-y-0 py-0">
          <select
            value={searchKind}
            onChange={(e) => setSearchKind(e.target.value)}
            className="h-9 rounded-control border border-subtle bg-surface px-2 text-body outline-none focus:border-accent"
          >
            {KINDS.map((k) => (<option key={k} value={k}>{KIND_LABELS[k]}</option>))}
          </select>
          <Input
            value={search}
            onChange={setSearch}
            placeholder="Ara (film, dizi, anime, kitap…)"
            ariaLabel="Medya ara"
            className="min-w-52 flex-1"
          />
          <span className="basis-full border-t border-subtle sm:hidden" />
          <div className="flex max-w-full gap-1.5 overflow-x-auto">
            {[['', 'Tüm türler'], ...KINDS.map((k) => [k, KIND_LABELS[k]])].map(([value, label]) => (
              <button key={value} type="button" onClick={() => setKind(value)} className={cx("h-7 shrink-0 rounded-control border px-2.5 text-meta", kind === value ? "border-accent bg-accent-surface text-accent" : "border-subtle text-secondary")}>{label}</button>
            ))}
          </div>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="h-8 rounded-control border border-subtle bg-surface px-2 text-meta">
            <option value="">Tüm durumlar</option>
            {STATUSES.map((value) => <option key={value} value={value}>{STATUS_LABELS[value]}</option>)}
          </select>
        </Toolbar>

        {searchKind === "movie" && !settings?.["media.tmdb_key"] && (
          <p className="mt-2 text-meta text-warn">
            Film/Dizi araması için TMDB API key gerekli — Ayarlar → Media bağlantıları'na ekle.
          </p>
        )}

        {activeTerm.length >= 2 && (
          <div className="mt-3">
            <div className="mb-2 flex flex-wrap gap-1.5">
              {QUICK_SITES.map(([name, base]) => (
                <a key={name} href={base + encodeURIComponent(activeTerm)} target="_blank" rel="noreferrer"
                  className="flex h-7 items-center gap-1 rounded border border-subtle px-2 text-meta text-secondary transition hover:border-strong hover:text-primary">
                  <ExternalLink size={11} /> {name}
                </a>
              ))}
            </div>
            {searching ? (
              <p className="text-meta text-muted">Aranıyor…</p>
            ) : results.length === 0 ? (
              <p className="text-meta text-muted">Sonuç yok — elle ekle: aşağıdan "elle ekle" bölümünü kullan.</p>
            ) : (
              <RowList as="ul">
                {results.map((hit) => (
                  <li key={hit.title} className="flex items-center gap-3 py-2">
                    <Cover url={hit.cover_url ?? null} title={hit.title} size="h-16 w-11" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-body text-primary">{hit.title}</p>
                      <p className="truncate text-meta text-muted">{(hit.subtitle ?? "") + (hit.year ? " · " + hit.year : "")}</p>
                    </div>
                    <Button size="sm" variant="primary" disabled={!online || addFromSearch.isPending}
                      onClick={() => addFromSearch.mutate(hit)}>
                      <Plus size={13} /> Ekle
                    </Button>
                  </li>
                ))}
              </RowList>
            )}
          </div>
        )}
      </Section>

      {/* ── Kütüphane ── */}
      <Section title="Kütüphane" hint={`${items.length} kayıt`}>{items.length === 0 ? (
        <Empty>Kütüphane boş — yukarıdan ara-ekle.</Empty>
      ) : (
        <RowList as="ul">
          {items.map((item) => {
            const open = expanded === item.id;
            const progressPct = item.total ? Math.min(100, Math.round(((item.progress ?? 0) / item.total) * 100)) : null;
            return (
              <li id={`media-item-${item.id}`} key={item.id} className="grid min-w-0 grid-cols-[48px_minmax(0,1fr)] gap-3 py-3 sm:grid-cols-[64px_minmax(0,1fr)_auto]">
                  <Cover url={String(item.meta?.cover_url ?? "") || null} title={item.title} size="h-20 w-12 sm:h-24 sm:w-16" />
                  <div className="min-w-0 flex-1">
                    <button data-media-focus="true" type="button" onClick={() => setExpanded(open ? null : item.id)} className="block w-full text-left">
                      <span className="block truncate text-body font-medium text-primary">{item.title}</span>
                    </button>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-meta text-muted">
                      <Badge>{KIND_LABELS[item.kind] ?? item.kind}</Badge>
                      <Badge tone={item.status === "completed" ? "ok" : item.status === "dropped" ? "neutral" : "warn"}>{STATUS_LABELS[item.status] ?? item.status}</Badge>
                      {item.score != null && (<span className="flex items-center gap-0.5 text-meta text-primary"><Star size={11} className="fill-current text-warn" /> {item.score}/10</span>)}
                      {progressPct !== null && (<span className="numeral text-[12px]">{item.progress}/{item.total}</span>)}
                    </div>
                    {progressPct !== null && (
                      <div className="mt-1.5 h-1 max-w-52 overflow-hidden rounded-full bg-surface-sunken">
                        <div className="h-full rounded-full bg-accent" style={{ width: progressPct + "%" }} />
                      </div>
                    )}
                    {item.notes && !open && (<p className="mt-1 line-clamp-1 text-meta text-secondary">{item.notes}</p>)}
                  </div>
                  <div className="col-span-2 flex flex-wrap items-start gap-2 sm:col-span-1 sm:justify-end">
                    {externalLinks(item, item.title).slice(0, 2).map(([name, url]) => (
                      <a key={name} href={url} target="_blank" rel="noreferrer" className="text-meta text-accent hover:underline">{name} ↗</a>
                    ))}
                    <Button size="sm" variant="danger" disabled={!online} onClick={() => confirmRemove(item)} title="Sil">
                      <Trash2 size={12} />
                    </Button>
                  </div>

                {open && (<div className="col-span-full"><MediaEditor item={item} onSave={(body) => update.mutate({ id: item.id, body })} /></div>)}
              </li>
            );
          })}
        </RowList>
      )}</Section>
    </PageFrame>
  );
}

function MediaEditor({ item, onSave }: { item: MediaItem; onSave: (body: Record<string, unknown>) => void }) {
  const [status, setStatus] = useState(item.status);
  const [progress, setProgress] = useState(item.progress ?? 0);
  const [total, setTotal] = useState(item.total ?? 0);
  const [score, setScore] = useState(item.score ?? 0);
  const [notes, setNotes] = useState(item.notes ?? "");
  return (
    <div className="mt-3 grid gap-3 border-t border-subtle pt-3 sm:grid-cols-2 lg:grid-cols-4">
      <label className="flex flex-col gap-1 text-meta text-muted">Durum
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="h-8 rounded-control border border-subtle bg-surface px-2 text-body text-primary outline-none">
          {STATUSES.map((s) => (<option key={s} value={s}>{STATUS_LABELS[s]}</option>))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-meta text-muted">İlerleme / toplam
        <div className="flex items-center gap-1.5">
          <input type="number" min={0} value={progress} onChange={(e) => setProgress(Number(e.target.value))} className="h-8 w-16 rounded-control border border-subtle bg-surface px-2 text-body text-primary outline-none" />
          <span className="text-muted">/</span>
          <input type="number" min={0} value={total} onChange={(e) => setTotal(Number(e.target.value))} className="h-8 w-16 rounded-control border border-subtle bg-surface px-2 text-body text-primary outline-none" />
        </div>
      </label>
      <label className="flex flex-col gap-1 text-meta text-muted">Puan (0-10)
        <select value={score} onChange={(e) => setScore(Number(e.target.value))} className="h-8 rounded-control border border-subtle bg-surface px-2 text-body text-primary outline-none">
          {Array.from({ length: 11 }, (_, i) => i).map((n) => (<option key={n} value={n}>{n}</option>))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-meta text-muted">Not
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={1} className="h-8 resize-y rounded-control border border-subtle bg-surface px-2 py-1 text-body text-primary outline-none" />
      </label>
      <div className="flex items-end gap-2 sm:col-span-2">
        <Button variant="primary" size="sm" onClick={() => onSave({ status, progress, total, score, notes })}>Kaydet</Button>
      </div>
    </div>
  );
}
