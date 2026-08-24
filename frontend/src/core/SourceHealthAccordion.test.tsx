// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SourceHealthAccordion } from "./SourceHealthAccordion";
import type { SourceHealth } from "./types";

const runs: SourceHealth[] = [
  {
    source: "Haberler",
    status: "ok",
    items_found: 4,
    error: null,
    started_at: "2026-08-25T08:00:00.000Z",
    finished_at: "2026-08-25T08:00:01.000Z",
  },
  {
    source: "Fırsatlar",
    status: "error",
    items_found: 0,
    error: "Bağlantı zaman aşımına uğradı",
    started_at: "2026-08-25T07:00:00.000Z",
    finished_at: null,
  },
  {
    source: "Bültenler",
    status: "empty",
    items_found: 0,
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
    expect(screen.getByText("2 sorunlu")).toBeTruthy();

    rerender(<SourceHealthAccordion sources={runs} open onOpenChange={onOpenChange} />);
    expect(screen.getByText("Fırsatlar")).toBeTruthy();
    expect(screen.getByText("Bağlantı zaman aşımına uğradı")).toBeTruthy();

    const details = container.querySelector("details") as HTMLDetailsElement;
    details.open = false;
    details.dispatchEvent(new Event("toggle"));

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("shows an empty state when there are no runs", () => {
    render(<SourceHealthAccordion sources={[]} open onOpenChange={vi.fn()} />);

    expect(screen.getByText("Kayıt yok.")).toBeTruthy();
  });
});
