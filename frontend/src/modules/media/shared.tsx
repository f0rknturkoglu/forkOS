import { useState } from "react";
import {cx, identityClasses} from "@/core/ui";
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

/** toplam girilmemisse yuzde yok demektir. */
export function progressPct(item: Pick<MediaItem, "progress" | "total">): number | null {
  return item.total ? Math.min(100, Math.round(((item.progress ?? 0) / item.total) * 100)) : null;
}

/** Yerel kapaklar yalnız güvenli tek dosya adıyla servis edilir. */
export function mediaCoverUrl(item: Pick<MediaItem, "cover_path" | "cover_url" | "meta">): string | null {
  const path = item.cover_path ?? "";
  const assetPrefix = "/api/media/assets/";
  const name = path.startsWith(assetPrefix) ? path.slice(assetPrefix.length) : path;
  const safePath = !path.includes("\\") && !path.includes("?") && !path.includes("#") && !path.includes("%")
    && (path === name || path.startsWith(assetPrefix));
  if (safePath && name && /^[a-z0-9][a-z0-9._-]*\.(?:jpg|jpeg|png|webp)$/i.test(name)) {
    return `/api/media/assets/${encodeURIComponent(name)}`;
  }
  return item.cover_url ?? (String(item.meta?.cover_url ?? "") || null);
}

/** Canonical provider, legacy kayıtların meta.source alanına düşer. */
export function mediaProvider(item: Pick<MediaItem, "provider" | "meta">): string | null {
  return item.provider ?? (typeof item.meta?.source === "string" ? item.meta.source : null);
}

const PROVIDER_LABELS: Record<string, string> = {
  tmdb: "TMDB",
  anilist: "AniList",
  kitsu: "Kitsu",
  openlibrary: "OpenLibrary",
  itunes: "iTunes",
  google_books: "Google Books",
  musicbrainz: "MusicBrainz",
  igdb: "IGDB",
  rawg: "RAWG",
};

/** Sağlayıcı kimliğini okunabilir, metin taşıyan kısa etikete çevirir. */
export function providerLabel(provider: string | null | undefined): string | null {
  if (!provider) return null;
  return PROVIDER_LABELS[provider] ?? provider;
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

function asId(value: unknown): string | null {
  return typeof value === "string" || typeof value === "number" ? String(value) || null : null;
}

function identityFor(
  name: string,
  meta: Record<string, unknown>,
  provider?: string | null,
  providerId?: string | null,
  providerIds?: Record<string, unknown> | null,
  legacyKey?: string,
): string | null {
  if (provider === name) return asId(providerId) ?? asId(providerIds?.[name]) ?? asId(meta[legacyKey ?? name]);
  return asId(providerIds?.[name]) ?? asId(meta[legacyKey ?? name]);
}

/** Kayit/arama sonucu icin harici site kisa yollari; ture gore sinirli,
 *  keyword her zaman Ingilizce (original_title varsa o, yoksa baslik). */
export function externalLinks(
  kind: string,
  title: string,
  meta: Record<string, unknown>,
  provider?: string | null,
  providerId?: string | null,
  providerIds?: Record<string, unknown> | null,
): [string, string][] {
  const q = encodeURIComponent(String((meta as { original_title?: string }).original_title ?? title));
  const links: [string, string][] = [];
  if (kind === "anime" || kind === "manga") {
    const anilistId = identityFor("anilist", meta, provider, providerId, providerIds, "anilist_id");
    links.push(["AniList", anilistId
      ? "https://anilist.co/" + kind + "/" + encodeURIComponent(anilistId)
      : "https://anilist.co/search/" + kind + "?search=" + q]);
    links.push(["MyAnimeList", "https://myanimelist.net/search/all?q=" + q]);
  } else if (kind === "book") {
    const openLibraryId = identityFor("openlibrary", meta, provider, providerId, providerIds, "ol_key");
    const openLibraryPath = openLibraryId?.startsWith("/")
      ? openLibraryId
      : openLibraryId ? "/works/" + openLibraryId : null;
    links.push(["OpenLibrary", openLibraryPath
      ? "https://openlibrary.org" + openLibraryPath
      : "https://openlibrary.org/search?q=" + q]);
    links.push(["Goodreads", "https://www.goodreads.com/search?q=" + q]);
  } else if (kind === "movie") {
    const tmdbId = identityFor("tmdb", meta, provider, providerId, providerIds, "tmdb_id")?.replace(/^movie:/, "");
    links.push(["TMDB", tmdbId
      ? "https://www.themoviedb.org/movie/" + encodeURIComponent(tmdbId)
      : "https://www.themoviedb.org/search?query=" + q]);
    links.push(["Letterboxd", "https://letterboxd.com/search/" + q + "/"]);
    links.push(["IMDb", "https://www.imdb.com/find/?q=" + q]);
    links.push(["Rotten Tomatoes", "https://www.rottentomatoes.com/search?search=" + q]);
  } else if (kind === "show") {
    const tmdbId = identityFor("tmdb", meta, provider, providerId, providerIds, "tmdb_id")?.replace(/^tv:/, "");
    links.push(["TMDB", tmdbId
      ? "https://www.themoviedb.org/tv/" + encodeURIComponent(tmdbId)
      : "https://www.themoviedb.org/search?query=" + q]);
    links.push(["IMDb", "https://www.imdb.com/find/?q=" + q]);
    links.push(["Rotten Tomatoes", "https://www.rottentomatoes.com/search?search=" + q]);
  } else if (kind === "audiobook") {
    links.push(["Audible", "https://www.audible.com/search?keywords=" + q]);
    links.push(["Apple Books", "https://books.apple.com/us/search?term=" + q]);
  } else if (kind === "podcast") {
    const itunesId = identityFor("itunes", meta, provider, providerId, providerIds);
    links.push(["Apple Podcasts", itunesId
      ? "https://podcasts.apple.com/us/podcast/id" + encodeURIComponent(itunesId)
      : "https://podcasts.apple.com/us/search?term=" + q]);
    links.push(["Spotify", "https://open.spotify.com/search/" + q]);
  } else if (kind === "music") {
    const musicBrainzId = identityFor("musicbrainz", meta, provider, providerId, providerIds);
    links.push(["Apple Music", "https://music.apple.com/us/search?term=" + q]);
    links.push(["MusicBrainz", musicBrainzId
      ? "https://musicbrainz.org/release-group/" + encodeURIComponent(musicBrainzId)
      : "https://musicbrainz.org/search?query=" + q + "&type=release_group"]);
    links.push(["RateYourMusic", "https://rateyourmusic.com/search?searchterm=" + q]);
  } else if (kind === "game") {
    const rawgId = identityFor("rawg", meta, provider, providerId, providerIds);
    links.push(["RAWG", rawgId
      ? "https://rawg.io/games/" + encodeURIComponent(rawgId)
      : "https://rawg.io/search?search=" + q]);
    links.push(["HowLongToBeat", "https://howlongtobeat.com/?q=" + q]);
  }
  return links;
}

/** Tür kimlik renginde dolgu (ilerleme çubuğu, vurgu). Statik sinif adlari
 *  (Tailwind JIT calisma zamani birlestirmez). */
const KIND_BG: Record<string, string> = {
  movie: "bg-[color:var(--kind-movie)]",
  show: "bg-[color:var(--kind-show)]",
  anime: "bg-[color:var(--kind-anime)]",
  manga: "bg-[color:var(--kind-manga)]",
  book: "bg-[color:var(--kind-book)]",
  audiobook: "bg-[color:var(--kind-audiobook)]",
  podcast: "bg-[color:var(--kind-podcast)]",
  music: "bg-[color:var(--kind-music)]",
  game: "bg-[color:var(--kind-game)]",
};

export function kindBg(kind: string): string {
  return KIND_BG[kind] ?? "bg-accent";
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
              : cx(kind ? identityClasses("kind-" + kind) : "border-subtle text-secondary hover:border-strong hover:text-primary"),
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
  google_books: "text-[color:var(--src-google-books)] border-[color:var(--src-google-books)]",
  musicbrainz: "text-[color:var(--src-musicbrainz)] border-[color:var(--src-musicbrainz)]",
  igdb: "text-[color:var(--src-igdb)] border-[color:var(--src-igdb)]",
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

/** Provider kimliğini kaynak renkli outline chip olarak sunar. */
export function providerChip(provider: string | null | undefined): string {
  return provider ? srcColor(provider) : "text-secondary border-subtle";
}

const SRC_BY_NAME: Record<string, string> = {
  TMDB: "tmdb", Letterboxd: "letterboxd", IMDb: "imdb", "Rotten Tomatoes": "rottentomatoes",
  AniList: "anilist", MyAnimeList: "mal", OpenLibrary: "openlibrary", Goodreads: "goodreads",
  Audible: "audible", Spotify: "spotify", RyM: "rym", RateYourMusic: "rym", HowLongToBeat: "hltb",
  "Google Books": "google_books", MusicBrainz: "musicbrainz", IGDB: "igdb",
};

/** Çerçeveli (outline) harici site bağlantıları — arayüzde her zaman görünür,
 *  her site kendi marka renginde. */
export function SiteLinks({ links, className }: { links: [string, string][]; className?: string }) {
  return (
    <span className={cx("flex flex-wrap items-center gap-1.5", className)}>
      {links.map(([name, url]) => (
        <a key={name} href={url} target="_blank" rel="noreferrer"
          className={cx("rounded border px-1.5 py-0.5 text-micro transition hover:opacity-80", srcColor(name))}>
          {name} ↗
        </a>
      ))}
    </span>
  );
}
