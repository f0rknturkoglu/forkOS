// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MediaLibraryControls, MediaMetrics, MediaPosterGrid } from "./MediaPosterGrid";
import { MediaSearchComposer } from "./MediaSearchComposer";

const dune = {
  id: "media-dune", title: "Dune", kind: "movie", status: "in_progress",
  progress: 4, total: 12, score: null, notes: null, started_at: null, finished_at: null,
  meta: {}, summary: null, release_date: null, progress_measure: "episode", review: null,
  favorite: false, owned: false, ownership: {}, monitored: false, provider: "tmdb",
  provider_id: "movie:438631", provider_ids: { tmdb: "438631" },
  cover_url: "https://remote.example/dune.jpg", cover_path: "dune-local.webp",
  backdrop_url: null, backdrop_path: null, last_synced_at: null, created_at: null,
  updated_at: null, archived_at: null,
};

const completed = {
  ...dune, id: "media-solo", title: "Solaris", kind: "book", status: "completed", progress: 1, total: 1,
  cover_path: null, cover_url: null, provider: "openlibrary",
};
const dropped = { ...dune, id: "media-dropped", title: "Dune: Messiah", status: "dropped" };

describe("MediaPosterGrid", () => {
  afterEach(cleanup);

  it("renders responsive posters with accessible covers and text-bearing metadata chips", () => {
    const { container } = render(<MediaPosterGrid items={[dune, completed]} online onQuick={vi.fn()} onTrash={vi.fn()} />);

    expect(container.querySelector("[data-media-grid]")?.className).toContain("auto-fill");
    expect(container.querySelectorAll("[data-media-poster]")).toHaveLength(2);
    expect(screen.getByRole("img", { name: "Dune kapağı" }).className).toContain("aspect-[2/3]");
    expect(screen.getByText("TMDB")).toBeTruthy();
    expect(screen.getAllByText("Film")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Dune ilerlemesini bir artır" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Dune detayını aç" }).getAttribute("href")).toBe("#/media/media-dune");
    const progress = screen.getByRole("progressbar", { name: "Dune ilerlemesi" });
    expect(progress.getAttribute("aria-valuemin")).toBe("0");
    expect(progress.getAttribute("aria-valuemax")).toBe("100");
    expect(progress.getAttribute("aria-valuenow")).toBe("33");
  });

  it("uses the local cover before remote urls, falls back to the initial, and omits quick actions for completed items", () => {
    const { container } = render(<MediaPosterGrid items={[dune, completed]} online onQuick={vi.fn()} onTrash={vi.fn()} />);

    expect(screen.getByRole("img", { name: "Dune kapağı" }).getAttribute("src")).toBe("/api/media/assets/dune-local.webp");
    expect(screen.getByRole("img", { name: "Solaris kapağı" }).textContent).toBe("S");
    expect(screen.queryByRole("button", { name: "Solaris ilerlemesini bir artır" })).toBeNull();
    expect(container.querySelectorAll(".h-px")).toHaveLength(2);
  });

  it("runs enabled quick actions but disables quick and trash actions while offline", () => {
    const onQuick = vi.fn();
    const { rerender } = render(<MediaPosterGrid items={[dune]} online onQuick={onQuick} onTrash={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Dune ilerlemesini bir artır" }));
    expect(onQuick).toHaveBeenCalledWith(dune);

    rerender(<MediaPosterGrid items={[dune]} online={false} onQuick={onQuick} onTrash={vi.fn()} />);
    expect((screen.getByRole("button", { name: "Dune ilerlemesini bir artır" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Dune işlemleri" }));
    expect((screen.getByRole("menuitem", { name: "Çöpe taşı" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("allows quick progress only for active statuses and never for dropped items", () => {
    const planned = { ...dune, id: "media-planned", title: "Arrival", status: "planned" };
    const paused = { ...dune, id: "media-paused", title: "Blade Runner", status: "paused" };
    render(<MediaPosterGrid items={[planned, paused, dropped]} online onQuick={vi.fn()} onTrash={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Arrival ilerlemesini bir artır" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Blade Runner ilerlemesini bir artır" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Dune: Messiah ilerlemesini bir artır" })).toBeNull();
  });
});

describe("MediaMetrics and MediaLibraryControls", () => {
  afterEach(cleanup);

  it("renders the four library metrics in one compact grid", () => {
    const { container } = render(<MediaMetrics stats={{ total: 8, in_progress: 2, completed: 3, planned: 2 }} />);
    const metrics = container.querySelector("[data-media-metrics]");
    const strip = metrics?.querySelector(".grid");
    expect(strip?.className).toContain("grid");
    expect(strip?.className).toContain("grid-cols-2");
    expect(strip?.className).toContain("sm:grid-cols-4");
    expect(screen.getByText("Toplam")).toBeTruthy();
    expect(screen.getByText("8")).toBeTruthy();
  });

  it("changes kind and status from library controls", () => {
    const onKindChange = vi.fn();
    const onStatusChange = vi.fn();
    const { container } = render(<MediaLibraryControls kind="movie" status="" onKindChange={onKindChange} onStatusChange={onStatusChange} />);

    fireEvent.click(screen.getByRole("button", { name: /Film/ }));
    fireEvent.change(screen.getByRole("combobox", { name: "Durum filtresi" }), { target: { value: "completed" } });
    expect(onKindChange).toHaveBeenCalledWith("movie");
    expect(onStatusChange).toHaveBeenCalledWith("completed");
    expect(container.querySelector("[data-media-library-controls]")).toBeTruthy();
  });

  it("does not place library filter chips inside the global composer", () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MediaSearchComposer online onAdded={vi.fn()} />
      </QueryClientProvider>,
    );
    expect(screen.queryByRole("group", { name: "Tür filtresi" })).toBeNull();
  });
});
