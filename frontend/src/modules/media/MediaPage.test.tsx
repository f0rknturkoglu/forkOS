import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { MediaItem } from "@/core/types";
import { Cover, externalLinks, KindChips, SiteLinks, statusLabel, statusLabelsFor } from "./shared";

const item = {
  id: "1", title: "Yabancı", kind: "book", status: "in_progress",
  progress: 60, total: 180, score: null, notes: null,
  started_at: null, finished_at: null,
  meta: { source: "openlibrary", ol_key: "/works/OL1W" },
  tags: [],
  created_at: null,
} satisfies MediaItem;

describe("media shared components", () => {
  it("cover falls back to the uppercase initial when url is missing", () => {
    const html = renderToStaticMarkup(<Cover url={null} title="yabancı" />);
    expect(html).toContain("Y");
    expect(html).not.toContain("<img");
  });

  it("renders the image while the url is intact", () => {
    const html = renderToStaticMarkup(
      <Cover url="https://example.com/x.jpg" title="Yabancı" size="h-14 w-10" />,
    );
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
    const links = externalLinks("movie", "Yıldızlararası", { source: "tmdb", tmdb_id: 157336, original_title: "Interstellar" });
    expect(links).toContainEqual(["Letterboxd", "https://letterboxd.com/search/Interstellar/"]);
    expect(links).toContainEqual(["Rotten Tomatoes", "https://www.rottentomatoes.com/search?search=Interstellar"]);
  });

  it("keeps music on RateYourMusic only", () => {
    const links = externalLinks("music", "Closer", {});
    expect(links).toContainEqual(["RyM", "https://rateyourmusic.com/search?searchterm=Closer"]);
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
    const html = renderToStaticMarkup(<SiteLinks links={[["Letterboxd", "https://letterboxd.com/search/Interstellar/"]]} />);
    expect(html).toContain("border-subtle");
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
