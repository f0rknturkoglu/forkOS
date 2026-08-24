import { useState } from "react";
import { cx } from "@/core/ui";
import type { MediaItem } from "@/core/types";

export const KINDS = ["movie", "show", "anime", "manga", "book", "audiobook", "podcast", "music", "game"] as const;
export const KIND_LABELS: Record<string, string> = {
  movie: "Film", show: "Dizi", anime: "Anime", manga: "Manga", book: "Kitap",
  audiobook: "Sesli Kitap", podcast: "Podcast", music: "Müzik", game: "Oyun",
};
export const STATUSES = ["planned", "in_progress", "paused", "completed", "dropped"] as const;
export const STATUS_LABELS: Record<string, string> = {
  planned: "Planlandı", in_progress: "Devam ediyor", paused: "Duraklatıldı",
  completed: "Tamamlandı", dropped: "Bırakıldı",
};

/** Tür bazlı durum adları. Değerler aynı; arayüz türün dilini konuşur. */
const STATUS_SETS: Record<string, Record<string, string>> = {
  movie: { planned: "İzlenecek", in_progress: "İzleniyor", paused: "Duraklatıldı", completed: "İzlendi", dropped: "Bırakıldı" },
  show: { planned: "İzlenecek", in_progress: "İzleniyor", paused: "Duraklatıldı", completed: "İzlendi", dropped: "Bırakıldı" },
  anime: { planned: "İzlenecek", in_progress: "İzleniyor", paused: "Duraklatıldı", completed: "İzlendi", dropped: "Bırakıldı" },
  game: { planned: "Oynanacak", in_progress: "Oynanıyor", paused: "Ara verildi", completed: "Bitirildi", dropped: "Bırakıldı" },
  music: { planned: "Dinlenecek", in_progress: "Dinleniyor", paused: "Duraklatıldı", completed: "Dinlendi", dropped: "Bırakıldı" },
  podcast: { planned: "Dinlenecek", in_progress: "Dinleniyor", paused: "Duraklatıldı", completed: "Dinlendi", dropped: "Bırakıldı" },
  audiobook: { planned: "Dinlenecek", in_progress: "Dinleniyor", paused: "Duraklatıldı", completed: "Dinlendi", dropped: "Bırakıldı" },
  book: { planned: "Okunacak", in_progress: "Okunuyor", paused: "Duraklatıldı", completed: "Okundu", dropped: "Bırakıldı" },
  manga: { planned: "Okunacak", in_progress: "Okunuyor", paused: "Duraklatıldı", completed: "Okundu", dropped: "Bırakıldı" },
};

/** Bir kaydın durum adı; bilinmeyen türde genel etikete düşer. */
export function statusLabel(kind: string, status: string): string {
  return STATUS_SETS[kind]?.[status] ?? STATUS_LABELS[status] ?? status;
}

/** Editör/filtre dropdown'ları için türün durum adları (STATUSES sırasıyla). */
export function statusLabelsFor(kind: string): Record<string, string> {
  return STATUS_SETS[kind] ?? STATUS_LABELS;
}

const KIND_COLORS: Record<string, string> = {
  movie: "movie", show: "show", anime: "anime", manga: "manga", book: "book",
  audiobook: "audiobook", podcast: "podcast", music: "music", game: "game",
};

/** Tür kimlik rengi yazı sınıfı; bilinmeyen türde nötr. */
export function kindColor(kind: string): string {
  return KIND_COLORS[kind] ? `text-kind-${KIND_COLORS[kind]}` : "text-secondary";
}

/** Tür kimlik renginde chip/rozet sınıfı (kenarlık + yazı). */
export function kindChip(kind: string): string {
  return KIND_COLORS[kind]
    ? `border border-kind-${KIND_COLORS[kind]} text-kind-${KIND_COLORS[kind]}`
    : "border border-subtle text-secondary";
}

/** toplam girilmemisse yuzde yok demektir. */
export function progressPct(item: Pick<MediaItem, "progress" | "total">): number | null {
  return item.total ? Math.min(100, Math.round(((item.progress ?? 0) / item.total) * 100)) : null;
}

/** Kapak yoksa ya da URL kiriksa bas harf yedegi. */
export function Cover({ url, title, size = "h-24 w-16" }: { url: string | null; title: string; size?: string }) {
  const [broken, setBroken] = useState(false);
  if (url && !broken) {
    return (
      <img
        src={url}
        alt=""
        onError={() => setBroken(true)}
        className={cx("shrink-0 rounded object-cover", size)}
      />
    );
  }
  return (
    <div className={cx("flex shrink-0 items-center justify-center rounded border border-subtle bg-surface-sunken font-serif text-heading text-secondary", size)}>
      {(title.trim().charAt(0) || "?").toUpperCase()}
    </div>
  );
}

/** Kayit/arama sonucu icin harici site kisa yollari; ture gore sinirli,
 *  keyword her zaman Ingilizce (original_title varsa o, yoksa baslik). */
export function externalLinks(kind: string, title: string, meta: Record<string, unknown>): [string, string][] {
  const q = encodeURIComponent(String((meta as { original_title?: string }).original_title ?? title));
  const links: [string, string][] = [];
  if (kind === "anime" || kind === "manga") {
    if (meta.source === "anilist" && meta.anilist_id) {
      links.push(["AniList", "https://anilist.co/" + kind + "/" + String(meta.anilist_id)]);
    }
    links.push(["MyAnimeList", "https://myanimelist.net/search/all?q=" + q]);
  } else if (kind === "book") {
    if (meta.source === "openlibrary" && meta.ol_key) {
      links.push(["OpenLibrary", "https://openlibrary.org" + String(meta.ol_key)]);
    }
    links.push(["Goodreads", "https://www.goodreads.com/search?q=" + q]);
  } else if (kind === "movie") {
    if (meta.source === "tmdb" && meta.tmdb_id) {
      links.push(["TMDB", "https://www.themoviedb.org/movie/" + String(meta.tmdb_id)]);
    }
    links.push(["Letterboxd", "https://letterboxd.com/search/" + q + "/"]);
    links.push(["IMDb", "https://www.imdb.com/find/?q=" + q]);
    links.push(["Rotten Tomatoes", "https://www.rottentomatoes.com/search?search=" + q]);
  } else if (kind === "show") {
    if (meta.source === "tmdb" && meta.tmdb_id) {
      links.push(["TMDB", "https://www.themoviedb.org/tv/" + String(meta.tmdb_id)]);
    }
    links.push(["IMDb", "https://www.imdb.com/find/?q=" + q]);
  } else if (kind === "audiobook") {
    links.push(["Audible", "https://www.audible.com/search?keywords=" + q]);
  } else if (kind === "podcast") {
    links.push(["Spotify", "https://open.spotify.com/search/" + q]);
  } else if (kind === "music") {
    links.push(["RyM", "https://rateyourmusic.com/search?searchterm=" + q]);
  } else if (kind === "game") {
    links.push(["HowLongToBeat", "https://howlongtobeat.com/?q=" + q]);
  }
  return links;
}

/** Tür kimlik renginde dolgu (ilerleme çubuğu, vurgu). */
export function kindBg(kind: string): string {
  return KIND_COLORS[kind] ? `bg-kind-${KIND_COLORS[kind]}` : "bg-accent";
}

/** Tur dagilimi cipleri; tiklanabilir filtre. "Tumu" her zaman basta. */
export function KindChips({
  counts, value, onChange,
}: {
  counts: Record<string, number>;
  value: string;
  onChange: (kind: string) => void;
}) {
  const chips: [string, string, number][] = [
    ["", "Tümü", Object.values(counts).reduce((sum, n) => sum + n, 0)],
    ...KINDS.filter((k) => counts[k]).map((k) => [k, KIND_LABELS[k], counts[k]] as [string, string, number]),
  ];
  return (
    <div className="flex max-w-full flex-wrap gap-1.5" role="group" aria-label="Tür filtresi">
      {chips.map(([kind, label, count]) => (
        <button
          key={kind}
          type="button"
          aria-pressed={value === kind}
          onClick={() => onChange(kind)}
          className={cx(
            "h-7 rounded-control border px-2.5 text-meta transition",
            value === kind
              ? "border-accent bg-accent-surface text-accent"
              : cx(kind ? kindChip(kind) : "border-subtle text-secondary hover:border-strong hover:text-primary"),
          )}
        >
          {label} <span className="numeral opacity-70">{count}</span>
        </button>
      ))}
    </div>
  );
}

/** Kaynak marka renkleri — index.css'teki --src-* değişkenleri. */
const SRC_CLASSES: Record<string, string> = {
  tmdb: "text-[color:var(--src-tmdb)] border-[color:var(--src-tmdb)]",
  anilist: "text-[color:var(--src-anilist)] border-[color:var(--src-anilist)]",
  kitsu: "text-[color:var(--src-kitsu)] border-[color:var(--src-kitsu)]",
  openlibrary: "text-[color:var(--src-openlibrary)] border-[color:var(--src-openlibrary)]",
  itunes: "text-[color:var(--src-itunes)] border-[color:var(--src-itunes)]",
  rawg: "text-[color:var(--src-rawg)] border-[color:var(--src-rawg)]",
  letterboxd: "text-[color:var(--src-letterboxd)] border-[color:var(--src-letterboxd)]",
  imdb: "text-[color:var(--src-imdb)] border-[color:var(--src-imdb)]",
  rottentomatoes: "text-[color:var(--src-rottentomatoes)] border-[color:var(--src-rottentomatoes)]",
  mal: "text-[color:var(--src-mal)] border-[color:var(--src-mal)]",
  goodreads: "text-[color:var(--src-goodreads)] border-[color:var(--src-goodreads)]",
  audible: "text-[color:var(--src-audible)] border-[color:var(--src-audible)]",
  spotify: "text-[color:var(--src-spotify)] border-[color:var(--src-spotify)]",
  rym: "text-[color:var(--src-rym)] border-[color:var(--src-rym)]",
  hltb: "text-[color:var(--src-hltb)] border-[color:var(--src-hltb)]",
};

/** Bağlantı/badge adı -> marka renk sınıfı (kenarlık + yazı). */
export function srcColor(name: string): string {
  const key = SRC_CLASSES[name] ? name : SRC_BY_NAME[name];
  return SRC_CLASSES[key] ?? "text-secondary border-subtle";
}

const SRC_BY_NAME: Record<string, string> = {
  TMDB: "tmdb", Letterboxd: "letterboxd", IMDb: "imdb", "Rotten Tomatoes": "rottentomatoes",
  AniList: "anilist", MyAnimeList: "mal", OpenLibrary: "openlibrary", Goodreads: "goodreads",
  Audible: "audible", Spotify: "spotify", RyM: "rym", HowLongToBeat: "hltb",
};

/** Çerçeveli (outline) harici site bağlantıları — arayüzde her zaman görünür,
 *  her site kendi marka renginde. */
export function SiteLinks({ links, className }: { links: [string, string][]; className?: string }) {
  return (
    <span className={cx("flex flex-wrap items-center gap-1.5", className)}>
      {links.map(([name, url]) => (
        <a key={name} href={url} target="_blank" rel="noreferrer"
          className={cx("rounded border px-1.5 py-0.5 text-[11px] transition hover:opacity-80", srcColor(name))}>
          {name} ↗
        </a>
      ))}
    </span>
  );
}
