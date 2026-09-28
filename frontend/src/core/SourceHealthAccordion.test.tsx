// @vitest-environment jsdom

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SourceHealthAccordion } from "./SourceHealthAccordion";
import type { SourceHealth } from "./types";

const runs: SourceHealth[] = [
  {
    source: "Haberler",
    status: "ok",
    items_found: 4,
    items_seen: 4,
    circuit_open: false,
    consecutive_failures: 0,
    error: null,
    started_at: "2026-08-25T08:00:00.000Z",
    finished_at: "2026-08-25T08:00:01.000Z",
  },
  {
    source: "Fırsatlar",
    status: "error",
    items_found: 0,
    items_seen: 0,
    circuit_open: false,
    consecutive_failures: 0,
    error: "Bağlantı zaman aşımına uğradı",
    started_at: "2026-08-25T07:00:00.000Z",
    finished_at: null,
  },
  {
    source: "Bültenler",
    status: "empty",
    items_found: 0,
    items_seen: 0,
    circuit_open: false,
    consecutive_failures: 0,
    error: null,
    started_at: "2026-08-25T06:00:00.000Z",
    finished_at: "2026-08-25T06:00:01.000Z",
  },
];

describe("SourceHealthAccordion", () => {
  it("summarizes closed runs and reports native disclosure changes", () => {
    const onOpenChange = vi.fn();
    const { container, rerender } = render(
      <SourceHealthAccordion sources={runs} open={false} onOpenChange={onOpenChange} />,
    );

    expect(container.querySelector("details")?.hasAttribute("open")).toBe(false);
    expect(screen.getByText("3 kayıt")).toBeTruthy();
    expect(screen.getByText("1 sağlıklı")).toBeTruthy();
    // `empty` (yeni kayıt yok) SORUN değildir: yalnız error/kısmi/yarım kaldı
    // "ilgi istiyor" sayılır.
    expect(screen.getByText("1 ilgi istiyor")).toBeTruthy();
    expect(screen.queryByText(/sorunlu/)).toBeNull();

    rerender(<SourceHealthAccordion sources={runs} open onOpenChange={onOpenChange} />);
    expect(screen.getByText("Fırsatlar")).toBeTruthy();
    expect(screen.getByText("Bağlantı zaman aşımına uğradı")).toBeTruthy();
    // Ham enum yerine tek sözlükten etiket.
    expect(screen.getByText("hata")).toBeTruthy();
    expect(screen.getByText("yeni kayıt yok")).toBeTruthy();

    const details = container.querySelector("details") as HTMLDetailsElement;
    details.open = false;
    details.dispatchEvent(new Event("toggle"));

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("kapalı kaynağı sorun saymaz ve nötr gösterir", () => {
    // Bu dosyada global cleanup yok: sorgular kendi konteynerine kapsanir.
    const { container } = render(
      <SourceHealthAccordion
        sources={[
          {
            source: "Haberler",
            status: "disabled",
            items_found: 0,
            items_seen: 0,
            circuit_open: false,
            consecutive_failures: 0,
            error: null,
            started_at: "2026-08-25T08:00:00.000Z",
            finished_at: null,
          },
        ]}
        open
        onOpenChange={vi.fn()}
      />,
    );
    const view = within(container);

    expect(view.getByText("kapalı")).toBeTruthy();
    expect(view.queryByText(/ilgi istiyor/)).toBeNull();
    expect(view.queryByText(/sorunlu/)).toBeNull();
  });

  it("shows an empty state when there are no runs", () => {
    render(<SourceHealthAccordion sources={[]} open onOpenChange={vi.fn()} />);

    expect(screen.getByText("Kayıt yok.")).toBeTruthy();
  });
});
