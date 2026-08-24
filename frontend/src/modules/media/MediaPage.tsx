import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Check, ExternalLink, ListTodo, MoreHorizontal, Play, Plus, RotateCcw, Search, Star, Trash2, X,
} from "lucide-react";
import { api } from "@/core/api";
import {
  Button, Empty, Field, IconButton, Input, PageFrame, PageHeader,
  Section, Select, Surface, Textarea, Toolbar, cx, useToast,
} from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { navigate } from "@/app/router";
import { useInvalidate, useOnline } from "@/lib/hooks";
import type { MediaItem, MediaStats, MetadataResult } from "@/core/types";
import {
  Cover, KINDS, KIND_LABELS, KindChips, STATUSES, SiteLinks, externalLinks,
  kindBg, kindChip, kindColor, progressPct, srcColor, statusLabel, statusLabelsFor,
} from "./shared";

/** Arama türüne göre hızlı site çipleri. Keyword İngilizce gider. */
const QUICK_SITES: Record<string, [string, string][]> = {
  movie: [
    ["TMDB", "https://www.themoviedb.org/search?query="],
    ["Letterboxd", "https://letterboxd.com/search/"],
    ["IMDb", "https://www.imdb.com/find/?q="],
    ["Rotten Tomatoes", "https://www.rottentomatoes.com/search?search="],
  ],
  show: [
    ["TMDB", "https://www.themoviedb.org/search?query="],
    ["IMDb", "https://www.imdb.com/find/?q="],
  ],
  anime: [
    ["AniList", "https://anilist.co/search/"],
    ["MyAnimeList", "https://myanimelist.net/search/all?q="],
  ],
  manga: [
    ["AniList", "https://anilist.co/search/"],
    ["MyAnimeList", "https://myanimelist.net/search/all?q="],
  ],
  book: [
    ["OpenLibrary", "https://openlibrary.org/search?q="],
    ["Goodreads", "https://www.goodreads.com/search?q="],
  ],
  audiobook: [["Audible", "https://www.audible.com/search?keywords="]],
  podcast: [["Spotify", "https://open.spotify.com/search/"]],
  music: [["RyM", "https://rateyourmusic.com/search?searchterm="]],
  game: [["HowLongToBeat", "https://howlongtobeat.com/?q="]],
};

/** Medya kaydından todo üretirken kullanılacak fiil. */
const STATUS_VERBS: Record<string, string> = {
  movie: "İzle", show: "İzle", anime: "İzle",
  game: "Oyna", music: "Dinle", podcast: "Dinle", audiobook: "Dinle",
  book: "Oku", manga: "Oku",
};

/** Kaynak -> marka renk anahtarı. */
const SRC_KEY: Record<string, string> = {
  tmdb: "tmdb", anilist: "anilist", kitsu: "kitsu", openlibrary: "openlibrary",
  itunes: "itunes", rawg: "rawg",
};

/** Arama sonucu + hangi türden geldiği. "Tümü" modunda tür gruplarindan gelir. */
type Hit = MetadataResult & { _kind?: string };

/** Kaynağın kimlik rozeti: sağlayıcı adı + marka rengi. */
function srcBadge(kind: string, meta: Record<string, unknown>): { label: string; cls: string } {
  const source = String(meta.source ?? "");
  const key = SRC_KEY[source];
  if (source === "tmdb") return { label: kind === "movie" ? "TMDB · Film" : "TMDB · Dizi", cls: srcColor(key) };
  if (source === "anilist") return { label: "AniList", cls: srcColor(key) };
  if (source === "kitsu") return { label: "Kitsu", cls: srcColor(key) };
  if (source === "openlibrary") return { label: "OpenLibrary", cls: srcColor(key) };
  if (source === "rawg") return { label: "RAWG", cls: srcColor(key) };
  if (source === "itunes") {
    const sub = meta.itunes_kind === "podcast" ? "Podcast" : meta.itunes_kind === "music" ? "Müzik" : "Sesli Kitap";
    return { label: `iTunes · ${sub}`, cls: srcColor(key) };
  }
  return { label: KIND_LABELS[kind] ?? kind, cls: kindChip(kind) };
}

export function MediaPage() {
  const online = useOnline();
  const invalidate = useInvalidate();
  const toast = useToast();

  const [kind, setKind] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [searchKind, setSearchKind] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [linksFor, setLinksFor] = useState<string | null>(null);
  const [libTerm, setLibTerm] = useState("");

  // Yankılanmayı yavaşlat: her tuşta dış API'yi dövme.
  const [debouncedTerm, setDebouncedTerm] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebouncedTerm(search.trim()), 350);
    return () => clearTimeout(t);
  }, [search]);

  const query: Record<string, string> = {};
  if (kind) query.kind = kind;
  if (status) query.status = status;
  const { data: items = [] } = useQuery({
    queryKey: ["media", query],
    queryFn: () => api.get<MediaItem[]>("/media?" + new URLSearchParams(query)),
  });
  const { data: stats } = useQuery({
    queryKey: ["media-stats"],
    queryFn: () => api.get<MediaStats>("/media/stats"),
  });
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<Record<string, unknown>>("/settings"),
  });

  const haveTmdb = Boolean(settings?.["media.tmdb_key"] || settings?.["media.tmdb_token"]);
  const haveRawg = Boolean(settings?.["media.rawg_key"]);

  const { data: results = [], isFetching: searching, error: searchError } = useQuery({
    queryKey: ["media-search", searchKind, debouncedTerm, haveTmdb, haveRawg],
    enabled: debouncedTerm.length >= 2,
    queryFn: async () => {
      const q = encodeURIComponent(debouncedTerm);
      if (searchKind) {
        const hits = await api.get<MetadataResult[]>("/media/search?kind=" + searchKind + "&q=" + q);
        return hits.map((h) => ({ ...h, _kind: searchKind }));
      }
      // "Tümü": anahtarı olan her sağlayıcıda ara, sonuçları kaynağıyla birleştir.
      const jobs = [
        { kind: "movie", run: haveTmdb }, { kind: "show", run: haveTmdb },
        { kind: "anime", run: true }, { kind: "manga", run: true }, { kind: "book", run: true },
        { kind: "podcast", run: true }, { kind: "music", run: true }, { kind: "audiobook", run: true },
        { kind: "game", run: haveRawg },
      ];
      const settled = await Promise.allSettled(
        jobs.filter((j) => j.run)
          .map((j) => api.get<MetadataResult[]>("/media/search?kind=" + j.kind + "&q=" + q)),
      );
      const hits: Hit[] = [];
      let idx = 0;
      for (const job of jobs) {
        if (!job.run) continue;
        const s = settled[idx++];
        if (s.status === "fulfilled") hits.push(...s.value.map((h) => ({ ...h, _kind: job.kind })));
      }
      return hits;
    },
  });

  const refresh = () => invalidate("media", "media-stats", "activity");

  const addFromSearch = useMutation({
    mutationFn: ({ hit, hitKind }: { hit: Hit; hitKind: string }) =>
      api.post<MediaItem>("/media", {
        title: hit.title, kind: hitKind,
        meta: { ...hit.metadata, cover_url: hit.cover_url },
      }),
    onSuccess: () => { refresh(); toast.push("Kütüphaneye eklendi", { tone: "ok" }); },
    onError: (e: Error) => toast.push("Eklenemedi: " + e.message, { tone: "danger" }),
  });

  // Elle ekleme aramayla ayni uca gider; meta'siz kayit.
  const addManual = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post<MediaItem>("/media", body),
    onSuccess: () => { refresh(); toast.push("Kitaplığa eklendi", { tone: "ok" }); },
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

  // Medya kaydini todo olarak ac (title + entity link) ve todoya git.
  const todoFromItem = useMutation({
    mutationFn: async (item: MediaItem) => {
      const verb = STATUS_VERBS[item.kind] ?? "Takip et";
      const todo = await api.post<{ id: string }>("/todos", {
        title: `${verb}: ${item.title}`,
        description: `Medya kaydından oluşturuldu (${KIND_LABELS[item.kind] ?? item.kind}).`,
      });
      await api.post("/links", { from_id: item.id, to_id: todo.id, relation: "media_todo" });
      return todo;
    },
    onSuccess: () => {
      invalidate("todos");
      toast.push("Todo'ya eklendi — görevler sayfasına gidiliyor", { tone: "ok" });
      navigate("/todos");
    },
    onError: (e: Error) => toast.push("Todo eklenemedi: " + e.message, { tone: "danger" }),
  });

  async function confirmRemove(item: MediaItem) {
    const ok = await confirmDialog({
      title: "Kayıt silinsin mi?",
      body: <><strong className="font-medium text-primary">{item.title}</strong> kütüphaneden kalkar.</>,
      confirmLabel: "Sil", tone: "danger",
    });
    if (ok) remove.mutate(item.id);
  }

  // Kütüphane içi arama: başlık + etiket + not.
  const libNeedle = libTerm.trim().toLocaleLowerCase("tr");
  const visibleItems = libNeedle
    ? items.filter((i) =>
        i.title.toLocaleLowerCase("tr").includes(libNeedle) ||
        (i.tags ?? []).some((t) => t.toLocaleLowerCase("tr").includes(libNeedle)) ||
        (i.notes ?? "").toLocaleLowerCase("tr").includes(libNeedle))
    : items;

  return (
    <PageFrame className="space-y-5">
      {/* ── Başlık ve özet ── */}
      <PageHeader eyebrow="Takip" title="Medya" />
      <div className="flex flex-wrap items-center gap-1.5" aria-label="Özet">
        {[
          ["Toplam", stats?.total ?? 0, "text-primary"],
          ["Devam ediyor", stats?.in_progress ?? 0, "text-warn"],
          ["Tamamlandı", stats?.completed ?? 0, "text-ok"],
          ["Planlandı", stats?.planned ?? 0, "text-accent"],
        ].map(([label, value, color]) => (
          <span key={String(label)} className="flex items-center gap-1.5 rounded-control border border-subtle bg-surface px-2.5 py-1 text-meta text-secondary">
            <span className={cx("numeral text-body font-semibold", String(color))}>{value}</span>
            {String(label)}
          </span>
        ))}
      </div>

      {/* ── Ara + elle ekle (ortalanmış tek sütun) ── */}
      <div className="mx-auto max-w-3xl space-y-3">
        <Surface className="space-y-3 p-3">
          <Toolbar className="border-y-0 py-0">
            <Select value={searchKind} onChange={setSearchKind} ariaLabel="Arama türü" className="w-32">
              <option value="">Tümü</option>
              {KINDS.map((k) => (<option key={k} value={k}>{KIND_LABELS[k]}</option>))}
            </Select>
            <div className="relative min-w-40 flex-1">
              <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
              <Input
                value={search}
                onChange={setSearch}
                placeholder="Her yerde ara — TMDB, AniList, iTunes, RAWG…"
                ariaLabel="Medya ara"
                className="pl-8"
              />
            </div>
          </Toolbar>

          {!searchKind && (!haveTmdb || !haveRawg) && (
            <p className="text-meta text-warn">
              {!haveTmdb && "TMDB (film/dizi)"}{!haveTmdb && !haveRawg && " ve "}{!haveRawg && "RAWG (oyun)"}
              {" "}anahtarı eklenmemiş — o kaynaklar "Tümü"ye katılmaz. Ayarlar → Medya bağlantıları.
            </p>
          )}
          {searchKind === "game" && !haveRawg && (
            <p className="text-meta text-warn">
              Oyun araması için RAWG anahtarı gerekli — Ayarlar → Medya bağlantıları'na ekle.
            </p>
          )}

          <div className="border-t border-subtle" />
          <ManualAdd
            disabled={!online}
            saving={addManual.isPending}
            onSave={(body) => addManual.mutateAsync(body).then(() => true, () => false)}
          />
        </Surface>

        {debouncedTerm.length >= 2 && (
          <div>
            {searchKind && (QUICK_SITES[searchKind] ?? []).length > 0 && (
              <div className="mb-2 flex flex-wrap justify-center gap-1.5">
                {QUICK_SITES[searchKind].map(([name, base]) => {
                  const english = results[0]?.metadata?.original_title ?? debouncedTerm;
                  return (
                    <a key={name} href={base + encodeURIComponent(String(english))} target="_blank" rel="noreferrer"
                      className="flex h-7 items-center gap-1 rounded border border-subtle px-2 text-meta text-secondary transition hover:border-strong hover:text-primary">
                      <ExternalLink size={11} /> {name}
                    </a>
                  );
                })}
              </div>
            )}
            {searchError ? (
              <p className="text-center text-meta text-danger">Arama hatası: {String(searchError instanceof Error ? searchError.message : searchError)}</p>
            ) : searching ? (
              <p className="text-center text-meta text-muted">Aranıyor…</p>
            ) : results.length === 0 ? (
              <p className="text-center text-meta text-muted">Sonuç yok — elle ekleyebilirsin.</p>
            ) : (
              <ul className="max-h-[300px] space-y-0.5 overflow-y-auto overscroll-contain rounded-card border border-subtle bg-surface p-1">
                {results.map((hit) => {
                  const hitKind = hit._kind ?? searchKind;
                  const badge = srcBadge(hitKind, hit.metadata);
                  return (
                    <li key={hitKind + ":" + hit.title} className="flex items-center gap-3 rounded px-2 py-1.5 transition-colors hover:bg-surface-hover">
                      <Cover url={hit.cover_url} title={hit.title} size="h-14 w-10" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-body font-medium text-primary">{hit.title}</p>
                        <div className="mt-1 flex flex-wrap items-center gap-1.5">
                          <span className={cx("rounded px-1 py-px text-[10px]", badge.cls)}>{badge.label}</span>
                          <SiteLinks links={externalLinks(hitKind, hit.title, hit.metadata)} />
                        </div>
                      </div>
                      <Button size="sm" variant="primary" disabled={!online || addFromSearch.isPending}
                        onClick={() => addFromSearch.mutate({ hit, hitKind })}>
                        <Plus size={13} /> Ekle
                      </Button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </div>

      {/* ── Kütüphane ── */}
      <Section
        title="Kütüphane"
        hint={libNeedle ? `${visibleItems.length}/${items.length} kayıt` : `${items.length} kayıt`}
        action={
          <div className="flex items-center gap-2">
            <Select value={status} onChange={setStatus} ariaLabel="Durum filtresi">
              <option value="">Tüm durumlar</option>
              {STATUSES.map((value) => <option key={value} value={value}>{statusLabel(kind, value)}</option>)}
            </Select>
            <span className="relative">
              <Search size={13} className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-muted" />
              <Input value={libTerm} onChange={setLibTerm} placeholder="Kütüphanede ara…" ariaLabel="Kütüphanede ara"
                className="w-44 pl-7 sm:w-52" />
            </span>
          </div>
        }
      >
        {stats && Object.keys(stats.by_kind).length > 0 && (
          <div className="mb-3">
            <KindChips counts={stats.by_kind} value={kind} onChange={setKind} />
          </div>
        )}
        {visibleItems.length === 0 ? (
          <Empty variant="page" title={libNeedle ? "Eşleşme yok" : "Kütüphane boş"}>
            {libNeedle ? "Farklı bir terim dene ya da filtreleri sıfırla." : "Yukarıdan ara-ekle ya da elle bir kayıt oluştur."}
          </Empty>
        ) : (
          <ul className="grid grid-cols-2 items-stretch gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {visibleItems.map((item) => {
              const open = expanded === item.id;
              const pct = progressPct(item);
              const cover = String(item.meta?.cover_url ?? "") || null;
              const tags = item.tags ?? [];
              const links = externalLinks(item.kind, item.title, item.meta ?? {});
              const linksOpen = linksFor === item.id;
              return (
                <li key={item.id} className={cx("relative flex h-full min-w-0 flex-col", open && "col-span-2 sm:col-span-3 lg:col-span-4 xl:col-span-5")}>
                  <div className={cx(
                    "flex h-full flex-col overflow-hidden rounded-card border bg-surface shadow-card transition",
                    open ? "border-accent-border" : "border-subtle hover:border-strong",
                  )}>
                    {open ? (
                      <div className="p-3.5">
                        <div className="mb-3 flex items-start gap-3">
                          <Cover url={cover} title={item.title} size="h-24 w-16" />
                          <div className="min-w-0 flex-1">
                            <h3 className="truncate font-serif text-heading text-primary">{item.title}</h3>
                            <p className={cx("mt-0.5 text-meta", kindColor(item.kind))}>
                              {KIND_LABELS[item.kind] ?? item.kind} · {statusLabel(item.kind, item.status)}
                            </p>
                            {item.score !== null && (
                              <span className="mt-1 flex items-center gap-0.5 text-meta text-primary">
                                <Star size={11} className="fill-current text-warn" /> {item.score}/10
                              </span>
                            )}
                            <div className="mt-2"><SiteLinks links={links} /></div>
                          </div>
                          <Button size="sm" variant="danger" disabled={!online} onClick={() => confirmRemove(item)} title="Sil">
                            <Trash2 size={12} />
                          </Button>
                        </div>
                        <MediaEditor item={item} onSave={(body) => update.mutate({ id: item.id, body })} />
                      </div>
                    ) : (
                      <>
                        <button type="button" onClick={() => setExpanded(item.id)} className="group relative block w-full shrink-0 text-left">
                          <div className="relative aspect-[2/3] w-full overflow-hidden bg-surface-sunken">
                            <div className="h-full w-full transition-transform duration-300 group-hover:scale-[1.04]">
                              <Cover url={cover} title={item.title} size="h-full w-full" />
                            </div>
                            <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/75 via-black/15 to-transparent" />
                            <span className={cx("absolute left-1.5 top-1.5 rounded px-1.5 py-0.5 text-[10px] bg-surface", kindChip(item.kind))}>
                              {statusLabel(item.kind, item.status)}
                            </span>
                            {item.score !== null && (
                              <span className="absolute right-1.5 top-1.5 flex items-center gap-0.5 rounded bg-surface px-1.5 py-0.5 text-[10px] text-primary">
                                <Star size={9} className="fill-current text-warn" /> {item.score}
                              </span>
                            )}
                            <div className="absolute inset-x-0 bottom-0 p-2">
                              <p className="truncate text-[13px] font-medium text-white drop-shadow">{item.title}</p>
                              <p className="mt-0.5 flex items-center gap-1.5 text-[10.5px] text-white/80">
                                {KIND_LABELS[item.kind] ?? item.kind}
                                {pct !== null && <span className="numeral text-white/70">{item.progress}/{item.total} · %{pct}</span>}
                              </p>
                              <div className="mt-1.5 h-[3px] w-full overflow-hidden rounded-full bg-white/25">
                                <div className={cx("h-full rounded-full transition-all", kindBg(item.kind))} style={{ width: (pct ?? 0) + "%" }} />
                              </div>
                            </div>
                          </div>
                          {tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 px-2 pb-1 pt-1.5">
                              {tags.slice(0, 3).map((tag) => (
                                <span key={tag} className="rounded border border-subtle px-1 py-px text-[10px] text-secondary">{tag}</span>
                              ))}
                              {tags.length > 3 && <span className="text-[10px] text-muted">+{tags.length - 3}</span>}
                            </div>
                          )}
                        </button>
                        <div className="mt-auto flex h-9 shrink-0 items-center gap-0.5 border-t border-subtle px-1.5">
                          <CardActions
                            item={item}
                            disabled={!online}
                            onUpdate={(body) => update.mutate({ id: item.id, body }, {
                              onSuccess: () => { if (body.status === "in_progress") navigate("/"); },
                            })}
                            onTodo={() => todoFromItem.mutate(item)}
                            onLinks={() => { setLinksFor(linksOpen ? null : item.id); setExpanded(null); }}
                            linksOpen={linksOpen}
                          />
                        </div>
                      </>
                    )}
                  </div>
                  {linksOpen && !open && (
                    <>
                      {/* Tık dışı kapatma katmanı */}
                      <div className="fixed inset-0 z-20" onClick={() => setLinksFor(null)} />
                      {/* Afişin dışında, kartın altında açılan popup */}
                      <div className="absolute right-1 top-full z-30 mt-1 w-44 rounded-card border border-strong bg-surface p-1.5 shadow-overlay">
                        <div className="mb-1 px-1 text-[10px] uppercase tracking-wide text-muted">Dış bağlantılar</div>
                        <SiteLinks links={links} className="gap-1" />
                      </div>
                    </>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </Section>
    </PageFrame>
  );
}

/** Kartın kompakt aksiyon satırı: başlat, +1, bitir, todo, dış bağlantılar (⋯). */
function CardActions({
  item, disabled, onUpdate, onTodo, onLinks, linksOpen,
}: {
  item: MediaItem;
  disabled: boolean;
  onUpdate: (body: Record<string, unknown>) => void;
  onTodo: () => void;
  onLinks: () => void;
  linksOpen: boolean;
}) {
  const buttons: { key: string; title: string; icon: React.ReactNode; body?: Record<string, unknown> }[] = [];
  const add = (b: typeof buttons[number]) => buttons.push(b);

  if (item.status === "planned") {
    add({ key: "start", title: "Başla", icon: <Play size={13} />, body: { status: "in_progress" } });
    add({ key: "finish", title: "Bitir", icon: <Check size={13} />, body: { status: "completed" } });
  } else if (item.status === "in_progress") {
    if (item.total && (item.progress ?? 0) < item.total) {
      add({ key: "next", title: "+1 bölüm", icon: <Plus size={13} />, body: { progress: (item.progress ?? 0) + 1 } });
    }
    add({ key: "finish", title: "Bitir", icon: <Check size={13} />, body: { status: "completed" } });
  } else if (item.status === "paused") {
    add({ key: "resume", title: "Devam", icon: <Play size={13} />, body: { status: "in_progress" } });
    add({ key: "finish", title: "Bitir", icon: <Check size={13} />, body: { status: "completed" } });
  } else if (item.status === "completed") {
    add({ key: "replay", title: "Tekrar", icon: <RotateCcw size={13} />, body: { status: "planned" } });
  } else {
    add({ key: "restore", title: "Geri al", icon: <RotateCcw size={13} />, body: { status: "planned" } });
  }

  return (
    <>
      {buttons.map(({ key, title, icon, body }) =>
        key === "next" ? (
          // Bölüm sayacı: çerçevenin içinde kalır, tooltip taşmaz.
          <button
            key={key}
            type="button"
            disabled={disabled}
            title="+1 bölüm"
            onClick={() => body && onUpdate(body)}
            className="flex h-6 shrink-0 items-center gap-1 rounded-control border border-subtle bg-surface px-1.5 text-[10.5px] text-secondary transition hover:border-strong hover:text-primary disabled:opacity-40"
          >
            <Plus size={11} /> {item.progress ?? 0}/{item.total}
          </button>
        ) : (
          <IconButton key={key} title={title} disabled={disabled} onClick={() => body && onUpdate(body)}>
            {icon}
          </IconButton>
        ),
      )}
      <IconButton title="Todo" disabled={disabled} onClick={onTodo}>
        <ListTodo size={13} />
      </IconButton>
      <span className="ml-auto">
        <IconButton title={linksOpen ? "Bağlantıları kapat" : "Bağlantılar"} onClick={onLinks} className={linksOpen ? "text-accent" : ""}>
          <MoreHorizontal size={13} />
        </IconButton>
      </span>
    </>
  );
}

/** Elle kayıt formu — arama kutusuyla yatay hizalanır, tek satırlık alanlar. */
function ManualAdd({
  disabled, saving, onSave,
}: {
  disabled: boolean;
  saving: boolean;
  onSave: (body: Record<string, unknown>) => Promise<boolean>;
}) {
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<string>("movie");
  const [status, setStatus] = useState("planned");
  const [total, setTotal] = useState("");
  const [notes, setNotes] = useState("");

  async function submit() {
    if (!title.trim()) return;
    const ok = await onSave({
      title: title.trim(),
      kind,
      status,
      total: total ? Number(total) : undefined,
      notes: notes.trim() || undefined,
    });
    if (ok) { setTitle(""); setTotal(""); setNotes(""); }
  }

  return (
    <div className="space-y-2">
      <form
        onSubmit={(e) => { e.preventDefault(); void submit(); }}
        className="flex flex-wrap items-end gap-2"
      >
        <Field label="Ad" className="min-w-44 flex-1 basis-64">
          <Input value={title} onChange={setTitle} placeholder="Örn. Yabancı" ariaLabel="Medya adı" autoFocus />
        </Field>
        <Field label="Tür" className="w-28">
          <Select value={kind} onChange={setKind}>
            {KINDS.map((k) => (<option key={k} value={k}>{KIND_LABELS[k]}</option>))}
          </Select>
        </Field>
        <Field label="Durum" className="w-40">
          <Select value={status} onChange={setStatus}>
            {STATUSES.map((s) => (<option key={s} value={s}>{statusLabelsFor(kind)[s]}</option>))}
          </Select>
        </Field>
        <Field label="Toplam" className="w-24" hint="Bölüm/kısım">
          <Input type="number" value={total} onChange={setTotal} placeholder="—" ariaLabel="Toplam bölüm sayısı" />
        </Field>
        <Button type="submit" variant="primary" disabled={disabled || saving || !title.trim()} className="mb-0.5">
          Ekle
        </Button>
      </form>
      <Field label="Not">
        <Textarea value={notes} onChange={setNotes} rows={1} placeholder="Nereden kaldım, öneren kim…" className="h-9 resize-y" />
      </Field>
    </div>
  );
}

function MediaEditor({ item, onSave }: { item: MediaItem; onSave: (body: Record<string, unknown>) => void }) {
  const [status, setStatus] = useState(item.status);
  const [progress, setProgress] = useState(String(item.progress ?? 0));
  const [total, setTotal] = useState(String(item.total ?? 0));
  const [score, setScore] = useState(String(item.score ?? 0));
  const [notes, setNotes] = useState(item.notes ?? "");
  const [tags, setTags] = useState<string[]>(item.tags ?? []);
  const [tagDraft, setTagDraft] = useState("");

  function commitTag() {
    const t = tagDraft.trim().replace(/,+$/, "");
    if (t && !tags.includes(t)) setTags([...tags, t]);
    setTagDraft("");
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        commitTag();
        onSave({
          status, progress: Number(progress), total: Number(total), score: Number(score),
          notes, tags,
        });
      }}
      className="grid gap-3 border-t border-subtle pt-3 sm:grid-cols-2 lg:grid-cols-4"
    >
      <Field label="Durum">
        <Select value={status} onChange={setStatus}>
          {STATUSES.map((s) => (<option key={s} value={s}>{statusLabelsFor(item.kind)[s]}</option>))}
        </Select>
      </Field>
      <Field label="İlerleme / toplam">
        <div className="flex items-center gap-1.5">
          <Input type="number" value={progress} onChange={setProgress} ariaLabel="İlerleme" className="w-full min-w-0 flex-1" />
          <span className="shrink-0 text-muted">/</span>
          <Input type="number" value={total} onChange={setTotal} ariaLabel="Toplam" className="w-full min-w-0 flex-1" />
        </div>
      </Field>
      <Field label="Puan (0-10)">
        <Select value={score} onChange={setScore}>
          {Array.from({ length: 11 }, (_, i) => i).map((n) => (<option key={n} value={String(n)}>{n}</option>))}
        </Select>
      </Field>
      <Field label="Not">
        <Textarea value={notes} onChange={setNotes} rows={1} className="h-9 resize-y" />
      </Field>
      <Field label="Etiketler" className="sm:col-span-2 lg:col-span-4">
        <div className="flex flex-wrap items-center gap-1.5 rounded border border-subtle bg-canvas px-2 py-1">
          {tags.map((t) => (
            <span key={t} className="flex items-center gap-1 rounded border border-subtle bg-surface px-1.5 py-0.5 text-[11px] text-secondary">
              {t}
              <button type="button" onClick={() => setTags(tags.filter((x) => x !== t))}
                aria-label={`${t} etiketini kaldır`} className="text-muted transition hover:text-danger">
                <X size={10} />
              </button>
            </span>
          ))}
          <input
            value={tagDraft}
            onChange={(e) => setTagDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); commitTag(); } }}
            onBlur={commitTag}
            placeholder={tags.length === 0 ? "Etiket ekle — örn. bilimkurgu, favori…" : ""}
            aria-label="Etiket ekle"
            className="min-w-24 flex-1 bg-transparent py-0.5 text-meta text-primary outline-none placeholder:text-muted"
          />
        </div>
      </Field>
      <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-4">
        <Button type="submit" variant="primary" size="sm">Kaydet</Button>
        <span className="text-meta text-muted">Etiketler todo ve yer imleriyle ortak havuzu kullanır.</span>
      </div>
    </form>
  );
}