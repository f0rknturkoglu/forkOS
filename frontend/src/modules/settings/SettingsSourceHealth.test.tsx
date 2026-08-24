// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SourceHealth } from "@/core/types";
import { SettingsSourceHealth } from "./SettingsPage";

const sources: SourceHealth[] = [
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
];

describe("SettingsSourceHealth", () => {
  it("starts closed and reveals source names when opened", () => {
    const { container } = render(<SettingsSourceHealth sources={sources} />);
    const details = container.querySelector("details[data-source-health]")!;

    expect(details.hasAttribute("open")).toBe(false);
    expect(screen.getByText("2 kayıt")).toBeTruthy();

    fireEvent.click(screen.getByText("Kaynak sağlığı"));

    expect(details.hasAttribute("open")).toBe(true);
    expect(screen.getByText("Haberler")).toBeTruthy();
    expect(screen.getByText("Fırsatlar")).toBeTruthy();
  });
});
