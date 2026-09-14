// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  EMPTY_MEDIA_FILTERS,
  MediaActiveFilters,
  MediaFilterPanel,
  MediaMetrics,
  MediaPosterGrid,
  MediaPosterGridSkeleton,
  type MediaFilterValues,
  type MediaPosterItem,
} from "./MediaPosterGrid";
import type { MediaItem } from "@/core/types";

const dune: MediaItem = {
  id: "media-dune",
  title: "Dune",
  kind: "movie",
  status: "in_progress",
  progress: 4,
  total: 12,
  score: null,
  notes: null,
  started_at: null,
  finished_at: null,
  meta: {},
  summary: null,
  release_date: null,
  progress_measure: "episode",
  review: null,
  favorite: false,
  owned: false,
  ownership: {},
  monitored: false,
  provider: "tmdb",
  provider_id: "movie:438631",
  provider_ids: { tmdb: "438631" },
  cover_url: "https://remote.example/dune.jpg",
  cover_path: "dune-local.webp",
  backdrop_url: null,
  backdrop_path: null,
  last_synced_at: null,
  created_at: null,
  updated_at: null,
  archived_at: null,
};

const completed = {
  ...dune,
  id: "media-solo",
  title: "Solaris",
  kind: "book",
  status: "completed",
  progress: 1,
  total: 1,
  cover_path: null,
  cover_url: null,
  provider: "openlibrary",
};
const dropped = { ...dune, id: "media-dropped", title: "Dune: Messiah", status: "dropped" };

function renderGrid(
  items: MediaItem[],
  props: {
    online?: boolean;
    onQuick?: (item: MediaPosterItem) => void;
    onTrash?: (item: MediaPosterItem) => void;
  } = {},
) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MediaPosterGrid
        items={items}
        online={props.online ?? true}
        onQuick={props.onQuick ?? (() => {})}
        onTrash={props.onTrash ?? (() => {})}
      />
    </QueryClientProvider>,
  );
}

describe("MediaPosterGrid", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () => new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }),
      ),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders responsive posters with accessible covers and text-bearing metadata chips", () => {
    const { container } = renderGrid([dune, completed]);

    expect(container.querySelector("[data-media-grid]")?.className).toContain("auto-fill");
    expect(container.querySelectorAll("[data-media-poster]")).toHaveLength(2);
    expect(screen.getByRole("img", { name: "Dune kapağı" }).className).toContain("aspect-[2/3]");
    expect(screen.getByText("TMDB")).toBeTruthy();
    expect(screen.getAllByText("Film")).toHaveLength(1);
    expect(screen.getByText("İzleniyor")).toBeTruthy();
    expect(screen.getByText("Okundu")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Dune için +1 bölüm" })).toBeNull();
    expect(screen.getByRole("link", { name: "Dune detayını aç" }).getAttribute("href")).toBe("#/media/media-dune");
    const progress = screen.getByRole("progressbar", { name: "Dune ilerlemesi" });
    expect(progress.getAttribute("aria-valuemin")).toBe("0");
    expect(progress.getAttribute("aria-valuemax")).toBe("100");
    expect(progress.getAttribute("aria-valuenow")).toBe("33");
  });

  it("shows the year, the monitored badge and a two-line title with a tooltip", () => {
    renderGrid([{ ...dune, release_date: "2024-11-08", monitored: true, meta: { year: 1999 } }]);

    const title = screen.getByRole("link", { name: "Dune detayını aç" });
    expect(screen.getByTitle("Dune")).toBeTruthy();
    const heading = screen.getByRole("link", { name: "Dune" });
    expect(heading.className).toContain("line-clamp-2");
    expect(heading.className).toContain("break-words");
    expect(title).toBeTruthy();
    expect(screen.getByText("2024")).toBeTruthy();
    expect(screen.queryByText("1999")).toBeNull();
    expect(screen.getByText("Takip ediliyor")).toBeTruthy();
    expect(screen.getByText("33%")).toBeTruthy();
  });

  it("falls back to the legacy meta year when release_date is absent", () => {
    renderGrid([{ ...dune, release_date: null, meta: { year: 1999 } }]);

    expect(screen.getByText("1999")).toBeTruthy();
  });

  it("uses the local cover before remote urls, falls back to the initial, and omits quick actions for completed items", () => {
    const { container } = renderGrid([dune, completed]);

    expect(screen.getByRole("img", { name: "Dune kapağı" }).getAttribute("src")).toBe(
      "/api/media/assets/dune-local.webp",
    );
    expect(screen.getByRole("img", { name: "Solaris kapağı" }).textContent).toBe("S");
    expect(screen.queryByRole("button", { name: "Solaris için +1 sayfa" })).toBeNull();
    expect(container.querySelectorAll('[role="progressbar"]')).toHaveLength(2);
  });

  it("replaces a broken cover image with the title initial", () => {
    renderGrid([dune]);

    fireEvent.error(screen.getByRole("img", { name: "Dune kapağı" }));

    expect(screen.getByRole("img", { name: "Dune kapağı" }).textContent).toBe("D");
    expect(screen.queryByRole("img", { name: "Dune kapağı" })?.tagName).toBe("DIV");
  });

  it("runs enabled quick actions but disables quick, collection and trash actions while offline", async () => {
    const user = userEvent.setup();
    const onQuick = vi.fn();
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: false });
    try {
      renderGrid([dune], { online: false, onQuick });
      fireEvent(window, new Event("offline"));

      expect(screen.queryByRole("button", { name: "Dune için +1 bölüm" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Koleksiyona ekle" })).toBeNull();
      await user.click(screen.getByRole("button", { name: "Dune işlemleri" }));
      expect((screen.getByRole("menuitem", { name: "Dune için +1 bölüm" }) as HTMLButtonElement).disabled).toBe(true);
      expect((screen.getByRole("menuitem", { name: "Çöpe taşı" }) as HTMLButtonElement).disabled).toBe(true);
      expect((screen.getByRole("menuitem", { name: "Koleksiyona ekle" }) as HTMLButtonElement).disabled).toBe(true);
    } finally {
      Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
      fireEvent(window, new Event("online"));
    }
  });

  it("runs the enabled quick action from the actions menu while online", async () => {
    const user = userEvent.setup();
    const onQuick = vi.fn();
    renderGrid([dune], { onQuick });

    await user.click(screen.getByRole("button", { name: "Dune işlemleri" }));
    await user.click(screen.getByRole("menuitem", { name: "Dune için +1 bölüm" }));

    expect(onQuick).toHaveBeenCalledWith(dune);
  });

  it("allows quick progress only for active statuses and never for dropped items", async () => {
    const user = userEvent.setup();
    const planned = { ...dune, id: "media-planned", title: "Arrival", status: "planned" };
    const paused = { ...dune, id: "media-paused", title: "Blade Runner", status: "paused" };
    renderGrid([planned, paused, dropped]);

    await user.click(screen.getByRole("button", { name: "Arrival işlemleri" }));
    expect(screen.getByRole("menuitem", { name: "Arrival için +1 bölüm" })).toBeTruthy();
    await user.keyboard("{Escape}");

    await user.click(screen.getByRole("button", { name: "Blade Runner işlemleri" }));
    expect(screen.getByRole("menuitem", { name: "Blade Runner için +1 bölüm" })).toBeTruthy();
    await user.keyboard("{Escape}");

    await user.click(screen.getByRole("button", { name: "Dune: Messiah işlemleri" }));
    expect(screen.queryByRole("menuitem", { name: "Dune: Messiah için +1 bölüm" })).toBeNull();
  });

  it("opens the card collection picker from the actions menu", async () => {
    const user = userEvent.setup();
    renderGrid([dune]);

    await user.click(screen.getByRole("button", { name: "Dune işlemleri" }));
    await user.click(screen.getByRole("menuitem", { name: "Koleksiyona ekle" }));

    expect(screen.queryByRole("menu", { name: "Dune işlemleri menüsü" })).toBeNull();
    expect(screen.getByRole("dialog", { name: "Koleksiyona ekle" })).toBeTruthy();
  });
});

describe("MediaPosterGridSkeleton", () => {
  afterEach(cleanup);

  it("reserves poster-card geometry while the first library page loads", () => {
    const { container } = render(<MediaPosterGridSkeleton count={4} />);

    const status = screen.getByRole("status", { name: "Kütüphane yükleniyor" });
    expect(status).toBeTruthy();
    expect(container.querySelector("[data-media-grid]")?.className).toContain("auto-fill");
    expect(container.querySelectorAll("[data-media-poster-skeleton]")).toHaveLength(4);
    expect(container.querySelectorAll("[data-media-poster-skeleton] .aspect-\\[2\\/3\\]")).toHaveLength(4);
    expect(container.querySelector("[data-media-poster-skeleton]")?.className).toContain("motion-safe:animate-pulse");
    expect(container.querySelector("[data-media-poster-skeleton]")?.className.split(" ")).not.toContain(
      "animate-pulse",
    );
  });
});

describe("MediaMetrics", () => {
  afterEach(cleanup);

  it("renders the four library metrics in one compact grid", () => {
    const { container } = render(<MediaMetrics stats={{ total: 8, in_progress: 2, completed: 3, planned: 2 }} />);
    const metrics = container.querySelector("[data-media-metrics]");
    const strip = metrics?.querySelector(".grid");
    expect(strip?.className).toContain("grid-cols-2");
    expect(strip?.className).toContain("sm:grid-cols-4");
    expect(screen.getByText("Toplam")).toBeTruthy();
    expect(screen.getByText("8")).toBeTruthy();
  });
});

describe("MediaFilterPanel", () => {
  afterEach(cleanup);

  function renderPanel(values: Partial<MediaFilterValues> = {}) {
    const onChange = vi.fn();
    const view = render(
      <MediaFilterPanel
        values={{ ...EMPTY_MEDIA_FILTERS, ...values }}
        onChange={onChange}
        providers={["tmdb", "rawg"]}
        collections={[{ id: "collection-1", title: "Favoriler" }]}
      />,
    );
    return { ...view, onChange };
  }

  it("wraps the kind chips instead of clipping them horizontally", () => {
    const { container } = renderPanel();
    const group = screen.getByRole("group", { name: "Tür filtresi" });

    expect(group.className).toContain("flex-wrap");
    expect(group.className).not.toContain("overflow-x-auto");
    expect(container.querySelector("[data-media-filters]")).toBeTruthy();
    expect(within(group).getByRole("button", { name: "Tümü" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("reports every advanced filter change", async () => {
    const user = userEvent.setup();
    const { onChange } = renderPanel({ kind: "movie" });

    await user.click(screen.getByRole("button", { name: "Kitap" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Durum filtresi" }), "completed");
    await user.selectOptions(screen.getByRole("combobox", { name: "Sağlayıcı filtresi" }), "rawg");
    await user.selectOptions(screen.getByRole("combobox", { name: "Koleksiyon filtresi" }), "collection-1");
    await user.selectOptions(screen.getByRole("combobox", { name: "Sıralama" }), "score");
    await user.click(screen.getByRole("checkbox", { name: "Sahip olduklarım" }));
    await user.click(screen.getByRole("checkbox", { name: "Favoriler" }));
    await user.click(screen.getByRole("checkbox", { name: "Takip ettiklerim" }));

    expect(onChange).toHaveBeenCalledWith({ kind: "book" });
    expect(onChange).toHaveBeenCalledWith({ status: "completed" });
    expect(onChange).toHaveBeenCalledWith({ provider: "rawg" });
    expect(onChange).toHaveBeenCalledWith({ collectionId: "collection-1" });
    expect(onChange).toHaveBeenCalledWith({ sort: "score" });
    expect(onChange).toHaveBeenCalledWith({ owned: true });
    expect(onChange).toHaveBeenCalledWith({ favorite: true });
    expect(onChange).toHaveBeenCalledWith({ monitored: true });
    expect(screen.getByText("Alaka sıralaması yalnızca arama sorgusu varken anlamlıdır.")).toBeTruthy();
  });

  it("commits the tag filter on blur and Enter instead of on every keystroke", async () => {
    const user = userEvent.setup();
    const { onChange } = renderPanel();
    const tag = screen.getByRole("textbox", { name: "Etiket filtresi" });

    await user.type(tag, "bilim kurgu");
    expect(onChange).not.toHaveBeenCalled();
    await user.tab();
    expect(onChange).toHaveBeenCalledWith({ tag: "bilim kurgu" });

    onChange.mockClear();
    await user.clear(tag);
    await user.type(tag, "klasik{Enter}");
    await user.click(screen.getByRole("button", { name: "Tümü" }));
    expect(onChange).toHaveBeenCalledWith({ tag: "klasik" });
  });

  it("clears the active kind when its chip is pressed again", async () => {
    const user = userEvent.setup();
    const { onChange } = renderPanel({ kind: "book" });

    await user.click(screen.getByRole("button", { name: "Kitap" }));

    expect(onChange).toHaveBeenCalledWith({ kind: "" });
  });
});

describe("MediaActiveFilters", () => {
  afterEach(cleanup);

  it("summarizes every active filter as a removable chip", async () => {
    const user = userEvent.setup();
    const onRemove = vi.fn();
    const onClear = vi.fn();
    render(
      <MediaActiveFilters
        values={{
          ...EMPTY_MEDIA_FILTERS,
          kind: "movie",
          status: "in_progress",
          provider: "tmdb",
          collectionId: "collection-1",
          tag: "klasik",
          sort: "score",
          owned: true,
          favorite: true,
          monitored: true,
        }}
        query="dune"
        collectionTitle="Favoriler"
        onRemove={onRemove}
        onClear={onClear}
      />,
    );

    expect(screen.getByText("Arama: dune")).toBeTruthy();
    expect(screen.getByText("Tür: Film")).toBeTruthy();
    expect(screen.getByText("Koleksiyon: Favoriler")).toBeTruthy();
    expect(screen.getByText("Sıralama: Puan")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Tür: Film filtresini kaldır" }));
    expect(onRemove).toHaveBeenCalledWith("kind");

    await user.click(screen.getByRole("button", { name: "Filtreleri temizle" }));
    expect(onClear).toHaveBeenCalled();
  });

  it("renders nothing when no filter is active", () => {
    const { container } = render(
      <MediaActiveFilters values={EMPTY_MEDIA_FILTERS} query="" onRemove={vi.fn()} onClear={vi.fn()} />,
    );

    expect(container.querySelector("[data-media-active-filters]")).toBeNull();
  });
});
