// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { SourceHealth } from "@/core/types";
import { SettingsSourceHealth } from "./SettingsSections";

afterEach(() => cleanup());

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
  it("summarizes broken sources in one line and links to the health page", () => {
    render(<SettingsSourceHealth sources={sources} />);
    expect(screen.getByText("1 kaynak hata veriyor")).toBeTruthy();
    const link = screen.getByRole("link", { name: "kaynak sağlığı" });
    expect(link.getAttribute("href")).toBe("#/health");
  });

  it("shows an all-healthy line when no source errored", () => {
    render(<SettingsSourceHealth sources={[sources[0]]} />);
    expect(screen.getByText("Tüm kaynaklar sağlıklı")).toBeTruthy();
    expect(screen.getByRole("link", { name: "kaynak sağlığı" }).getAttribute("href")).toBe("#/health");
  });
});
