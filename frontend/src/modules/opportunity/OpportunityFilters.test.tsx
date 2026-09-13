// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { OpportunityFilterBar } from "./OpportunityFilters";
import { browseQuery, type OpportunityBrowseFilters } from "./opportunityBrowse";
import { activeFilterChips, clearAllFilters, switchSection } from "./filterState";

const filters: OpportunityBrowseFilters = {
  section: "jobs",
  category: "software",
  region: "EU",
  remote: "remote",
  search: "react",
  min_score: 40,
  max_score: 80,
  sort: "score",
  offset: 0,
  limit: 60,
};

function renderBar(overrides: Partial<OpportunityBrowseFilters> = {}, extra: Record<string, unknown> = {}) {
  const onChange = vi.fn();
  const onView = vi.fn();
  render(
    <OpportunityFilterBar
      filters={{ ...filters, ...overrides }}
      facets={{}}
      shown={12}
      total={40}
      loading={false}
      view="rows"
      onView={onView}
      onChange={onChange}
      searchValue={String((extra.searchValue as string) ?? filters.search ?? "")}
      onSearchChange={() => undefined}
      liveMessage=""
      {...extra}
    />,
  );
  return { onChange, onView };
}

function openPanel() {
  fireEvent.click(screen.getByRole("button", { name: /Filtreler/ }));
}

describe("opportunity filter bar", () => {
  afterEach(cleanup);

  it("keeps the default surface compact: no slider track until the popover opens", () => {
    renderBar();
    expect(screen.queryByRole("slider", { name: /Minimum skor/ })).toBeNull();
    expect(screen.getByRole("button", { name: /Skor aralığı: 40–80/ })).toBeTruthy();
  });

  it("opens the compact score popover and shows the current range", () => {
    renderBar();
    fireEvent.click(screen.getByRole("button", { name: /Skor aralığı: 40–80/ }));
    expect(screen.getByRole("dialog", { name: "Skor aralığı" })).toBeTruthy();
    expect(screen.getByRole("slider", { name: /Minimum skor/ })).toBeTruthy();
    expect(screen.getByRole("slider", { name: /Maksimum skor/ })).toBeTruthy();
  });

  it("shows 'Tüm skorlar' when no score filter is active", () => {
    renderBar({ min_score: undefined, max_score: undefined });
    expect(screen.getByRole("button", { name: /Skor aralığı: Tüm skorlar/ })).toBeTruthy();
  });

  it("renders -1 as 'Elendi' on the score control", () => {
    renderBar({ min_score: -1, max_score: -1 });
    expect(screen.getByRole("button", { name: /Skor aralığı: Elendi/ })).toBeTruthy();
  });

  it("applies a score preset with consistent, non-overlapping bands", () => {
    const { onChange } = renderBar({ min_score: undefined, max_score: undefined });
    fireEvent.click(screen.getByRole("button", { name: /Skor aralığı: Tüm skorlar/ }));
    fireEvent.click(screen.getByRole("button", { name: "70–79" }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ min_score: 70, max_score: 79.99, offset: 0 }));
  });

  it("commits a slider drag exactly once, and not on every pointer move", () => {
    const { onChange } = renderBar();
    fireEvent.click(screen.getByRole("button", { name: /Skor aralığı: 40–80/ }));
    const minimum = screen.getByRole("slider", { name: /Minimum skor/ });
    fireEvent.change(minimum, { target: { value: "55" } });
    fireEvent.change(minimum, { target: { value: "56" } });
    fireEvent.change(minimum, { target: { value: "57" } });
    expect(onChange).not.toHaveBeenCalled();
    fireEvent.pointerUp(minimum);
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ min_score: 57 }));
  });

  it("supports keyboard adjustment of both handles", () => {
    const { onChange } = renderBar();
    fireEvent.click(screen.getByRole("button", { name: /Skor aralığı: 40–80/ }));
    const maximum = screen.getByRole("slider", { name: /Maksimum skor/ });
    fireEvent.change(maximum, { target: { value: "90" } });
    expect(maximum.getAttribute("aria-label")).toBe("Maksimum skor");
    fireEvent.pointerUp(maximum);
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ max_score: 90 }));
  });

  it("resets the score range", () => {
    const { onChange } = renderBar();
    fireEvent.click(screen.getByRole("button", { name: /Skor aralığı: 40–80/ }));
    fireEvent.click(screen.getByRole("button", { name: /Sıfırla/ }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ min_score: undefined, max_score: undefined }));
  });

  it("offers a %70+ profile match preset and never calls it a CV", () => {
    const { onChange } = renderBar({ min_skill_match: undefined, skill_tier: undefined });
    openPanel();
    fireEvent.click(screen.getByRole("button", { name: "%70+" }));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ min_skill_match: 0.7, skill_tier: "high", offset: 0 }),
    );
    expect(screen.queryByText(/CV Uyumu/)).toBeNull();
    expect(screen.getByText(/Profil .*beceri|Profil \/ beceri/i)).toBeTruthy();
  });

  it("selects the uncomputed profile-match state explicitly", () => {
    const { onChange } = renderBar({ min_skill_match: undefined, skill_tier: undefined });
    openPanel();
    fireEvent.click(screen.getByRole("button", { name: "Hesaplanmadı" }));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ skill_match_state: "uncomputed", min_skill_match: undefined }),
    );
  });

  it("renders every active filter as a removable chip", () => {
    renderBar({
      announcement_source: "ylsy",
      period_days: 30,
      year: 2026,
      status: "new",
      source: "manual",
      section: "announcements",
      min_score: undefined,
      max_score: undefined,
      category: undefined,
      region: undefined,
      remote: undefined,
    });
    const bar = screen.getByLabelText("Aktif filtreler");
    expect(bar.textContent).toContain("Arama: react");
    expect(bar.textContent).toContain("Kaynak:");
    expect(bar.textContent).toContain("Durum:");
    expect(bar.textContent).toContain("Duyuru: YLSY");
    expect(bar.textContent).toContain("Son 30 gün");
    expect(bar.textContent).toContain("Yıl: 2026");
  });

  it("removes only the clicked filter", () => {
    const { onChange } = renderBar();
    openPanel();
    fireEvent.click(screen.getByRole("button", { name: /Skor: 40–80 filtresini kaldır/ }));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ min_score: undefined, max_score: undefined, search: "react" }),
    );
  });

  it("never puts an emoji on the manual source label", () => {
    renderBar({ source: undefined });
    openPanel();
    const manual = screen.getByRole("button", { name: /Manuel Eklenenler/ });
    expect(manual.textContent).toContain("Manuel Eklenenler");
    expect(manual.textContent ?? "").not.toMatch(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/u);
  });

  it("shows a loading label instead of a fake 0/0 counter", () => {
    renderBar({}, { shown: 0, total: 0, loading: true });
    expect(screen.getByText("Yükleniyor…")).toBeTruthy();
    expect(screen.queryByText("0 / 0 kayıt")).toBeNull();
  });

  it("shows the counter once loaded", () => {
    renderBar({}, { shown: 60, total: 19117 });
    expect(screen.getByText("60 / 19117 kayıt")).toBeTruthy();
  });
});

describe("filter registry", () => {
  it("counts and clears every active filter", () => {
    const chips = activeFilterChips(filters);
    expect(chips.map((chip) => chip.label)).toEqual(
      expect.arrayContaining(["Arama: react", "Konum: Avrupa", "Çalışma: Uzaktan"]),
    );
    const cleared = clearAllFilters(filters);
    expect(activeFilterChips(cleared)).toHaveLength(0);
    expect(cleared.section).toBe("jobs");
  });

  it("keeps shared filters when switching to announcements but drops job-only ones", () => {
    const next = switchSection(filters, "announcements");
    expect(next.search).toBe("react");
    expect(next.min_score).toBeUndefined();
    expect(next.max_score).toBeUndefined();
    expect(next.remote).toBeUndefined();
    expect(next.category).toBeUndefined();
    expect(next.sort).toBe("newest");
    expect(activeFilterChips({ ...next, announcement_source: "ylsy" }).map((chip) => chip.label)).toContain(
      "Duyuru: YLSY",
    );
  });

  it("only sends workspace-appropriate query params", () => {
    expect(browseQuery(filters)).toContain("category=software");
    expect(browseQuery(filters)).toContain("min_score=40");
    expect(browseQuery({ ...filters, max_skill_match: 0.6999 })).toContain("max_skill_match=0.6999");
    expect(browseQuery({ ...filters, skill_match_state: "uncomputed" })).toContain("skill_match_state=uncomputed");
    const announcements = browseQuery(switchSection({ ...filters, announcement_source: "ylsy" }, "announcements"));
    expect(announcements).toContain("announcement_source=ylsy");
    expect(announcements).not.toContain("min_score=");
    expect(announcements).not.toContain("remote=");
    expect(announcements).not.toContain("skill_match_state=");
  });
});
