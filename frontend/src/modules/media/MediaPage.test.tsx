import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  Cover,
  externalLinks,
  KindChips,
  mediaCoverUrl,
  mediaProvider,
  providerChip,
  SiteLinks,
  statusLabel,
  statusLabelsFor,
} from "./shared";

const item = {
  id: "1",
  title: "Yabancı",
  kind: "book",
  status: "in_progress",
  progress: 60,
  total: 180,
  score: null,
  notes: null,
  started_at: null,
  finished_at: null,
  meta: { source: "openlibrary", ol_key: "/works/OL1W" },
  created_at: null,
};

describe("media shared components", () => {
  it("normalizes safe local covers before remote fallbacks and rejects unsafe paths", () => {
    const cachedName = "a".repeat(64) + ".webp";
    expect(mediaCoverUrl({ cover_path: cachedName, cover_url: "https://remote" })).toBe(
      `/api/media/assets/${cachedName}`,
    );
    expect(mediaCoverUrl({ cover_path: `/api/media/assets/${cachedName}`, cover_url: "https://remote" })).toBe(
      `/api/media/assets/${cachedName}`,
    );
    for (const path of [
      "../abc.webp",
      "/api/media/assets/../abc.webp",
      "/api/media/assets/%2e%2e%2fabc.webp",
      "abc.webp?token=secret",
      "abc.webp#fragment",
      "folder/abc.webp",
      "folder\\abc.webp",
    ])
      expect(mediaCoverUrl({ cover_path: path, cover_url: "https://remote" })).toBe("https://remote");
    expect(mediaCoverUrl({ cover_path: null, cover_url: null, meta: { cover_url: "https://legacy" } })).toBe(
      "https://legacy",
    );
  });

  it("prefers canonical provider identity and gives it a source chip", () => {
    expect(mediaProvider({ provider: "musicbrainz", meta: { source: "itunes" } })).toBe("musicbrainz");
    expect(providerChip("musicbrainz")).toContain("--src-musicbrainz");
  });

  it("offers only the external sites relevant to each media kind", () => {
    expect(externalLinks("music", "Closer", {}, "musicbrainz", "release-1", {})).toEqual(
      expect.arrayContaining([
        ["MusicBrainz", "https://musicbrainz.org/release-group/release-1"],
        ["Apple Music", "https://music.apple.com/us/search?term=Closer"],
        ["RateYourMusic", "https://rateyourmusic.com/search?searchterm=Closer"],
      ]),
    );

    const linkCases = [
      ["movie", ["TMDB", "IMDb", "Rotten Tomatoes", "Letterboxd"], ["RateYourMusic"]],
      ["show", ["TMDB", "IMDb", "Rotten Tomatoes"], ["Letterboxd"]],
      ["anime", ["AniList", "MyAnimeList"], ["Goodreads"]],
      ["manga", ["AniList", "MyAnimeList"], ["IMDb"]],
      ["book", ["OpenLibrary", "Goodreads"], ["IMDb"]],
      ["audiobook", ["Audible", "Apple Books"], ["Letterboxd"]],
      ["podcast", ["Apple Podcasts", "Spotify"], ["Goodreads"]],
      ["game", ["RAWG", "HowLongToBeat"], ["IMDb"]],
    ] as const;

    for (const [kind, required, forbidden] of linkCases) {
      const names = externalLinks(kind, "Dune", {}, undefined, undefined, {}).map(([name]) => name);
      expect(names).toEqual(expect.arrayContaining([...required]));
      for (const name of forbidden) expect(names).not.toContain(name);
    }
  });

  it("cover falls back to the uppercase initial when url is missing", () => {
    const html = renderToStaticMarkup(<Cover url={null} title="yabancı" />);
    expect(html).toContain("Y");
    expect(html).not.toContain("<img");
  });

  it("renders the image while the url is intact", () => {
    const html = renderToStaticMarkup(<Cover url="https://example.com/x.jpg" title="Yabancı" size="h-14 w-10" />);
    expect(html).toContain("<img");
    expect(html).toContain('src="https://example.com/x.jpg"');
  });

  it("derives external links from metadata source", () => {
    const links = externalLinks(item.kind, item.title, item.meta);
    expect(links).toContainEqual(["OpenLibrary", "https://openlibrary.org/works/OL1W"]);
    expect(links).toContainEqual(["Goodreads", "https://www.goodreads.com/search?q=Yabanc%C4%B1"]);
    expect(links.some(([name]) => name === "Letterboxd")).toBe(false);
  });

  it("maps tmdb source to tv and movie bases by kind", () => {
    const showLinks = externalLinks("show", "Severance", { source: "tmdb", tmdb_id: 42 });
    const movieLinks = externalLinks("movie", "Interstellar", { source: "tmdb", tmdb_id: 42 });
    expect(showLinks).toContainEqual(["TMDB", "https://www.themoviedb.org/tv/42"]);
    expect(movieLinks).toContainEqual(["TMDB", "https://www.themoviedb.org/movie/42"]);
  });

  it("falls back to legacy metadata IDs when canonical provider IDs are absent", () => {
    const links = externalLinks("movie", "Interstellar", { tmdb_id: 42 }, "tmdb", undefined, {});
    expect(links).toContainEqual(["TMDB", "https://www.themoviedb.org/movie/42"]);
  });

  it("opens movie shortcuts on Letterboxd, IMDb and Rotten Tomatoes but not RyM", () => {
    const links = externalLinks("movie", "Interstellar", { source: "tmdb", tmdb_id: 42 });
    const names = links.map(([name]) => name);
    expect(names).toEqual(expect.arrayContaining(["TMDB", "Letterboxd", "IMDb", "Rotten Tomatoes"]));
    expect(names).not.toContain("RyM");
    expect(links).toContainEqual(["Letterboxd", "https://letterboxd.com/search/Interstellar/"]);
    expect(links).toContainEqual(["IMDb", "https://www.imdb.com/find/?q=Interstellar"]);
    expect(links).toContainEqual(["Rotten Tomatoes", "https://www.rottentomatoes.com/search?search=Interstellar"]);
  });

  it("uses the English original_title for search keywords when present", () => {
    const links = externalLinks("movie", "Yıldızlararası", {
      source: "tmdb",
      tmdb_id: 157336,
      original_title: "Interstellar",
    });
    expect(links).toContainEqual(["Letterboxd", "https://letterboxd.com/search/Interstellar/"]);
    expect(links).toContainEqual(["Rotten Tomatoes", "https://www.rottentomatoes.com/search?search=Interstellar"]);
  });

  it("keeps music on RateYourMusic", () => {
    const links = externalLinks("music", "Closer", {});
    expect(links).toContainEqual(["RateYourMusic", "https://rateyourmusic.com/search?searchterm=Closer"]);
    expect(links.some(([name]) => name === "Letterboxd")).toBe(false);
  });

  it("speaks each kind's language for statuses", () => {
    expect(statusLabel("movie", "completed")).toBe("İzlendi");
    expect(statusLabel("game", "completed")).toBe("Bitirildi");
    expect(statusLabel("game", "in_progress")).toBe("Oynanıyor");
    expect(statusLabel("music", "planned")).toBe("Dinlenecek");
    expect(statusLabel("book", "completed")).toBe("Okundu");
    expect(statusLabel("unknown_kind", "planned")).toBe("Planlandı");
  });

  it("falls back to generic status labels for unknown kinds", () => {
    const labels = statusLabelsFor("bilinmeyen");
    expect(labels.completed).toBe("Tamamlandı");
    expect(statusLabelsFor("game").completed).toBe("Bitirildi");
  });

  it("renders outlined site links so they stand out in the UI", () => {
    const html = renderToStaticMarkup(
      <SiteLinks links={[["Letterboxd", "https://letterboxd.com/search/Interstellar/"]]} />,
    );
    expect(html).toContain("border-[color:var(--src-letterboxd)]");
    expect(html).toContain('href="https://letterboxd.com/search/Interstellar/"');
    expect(html).toContain("Letterboxd ↗");
  });

  it("renders kind chips with counts and pressed state", () => {
    const html = renderToStaticMarkup(
      <KindChips counts={{ book: 3, movie: 1 }} value="book" onChange={() => undefined} />,
    );
    expect(html).toContain("Tümü");
    expect(html).toContain("Kitap");
    expect(html).toContain(">3</span>");
    expect(html).toContain('aria-pressed="true"');
  });
});
