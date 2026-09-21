// @vitest-environment jsdom

/**
 * Ayarlar alt şeridi sözleşmesi.
 *
 * Kritik kural: veri gelmeden veya sorgu düştüğünde "sağlıklı" DENMEZ
 * (NO DATA ≠ HEALTHY). Şerit yüklenirken/hatalıyken bunu açıkça söyler ve
 * sağlık sayfasına giden bağlantı her durumda durur.
 */

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { SourceHealth } from "@/core/types";
import { SettingsSourceHealth } from "./SettingsSections";

afterEach(() => cleanup());

function run(overrides: Partial<SourceHealth> & { source: string; status: string }): SourceHealth {
  return {
    items_found: 0,
    error: null,
    started_at: "2026-09-22T08:00:00.000Z",
    finished_at: "2026-09-22T08:00:01.000Z",
    ...overrides,
  } as SourceHealth;
}

const healthLink = () => screen.getByRole("link", { name: "kaynak sağlığı" }).getAttribute("href");

describe("SettingsSourceHealth", () => {
  it("sağlıklı kaynakları tek satırda özetler", () => {
    render(
      <SettingsSourceHealth
        query={{
          data: [run({ source: "jobhunter:linkedin", status: "ok" }), run({ source: "rss:1", status: "ok" })],
          isLoading: false,
          isError: false,
        }}
      />,
    );
    expect(screen.getByText("2 kaynak sağlıklı")).toBeTruthy();
    expect(healthLink()).toBe("#/health");
  });

  it("ilgi isteyen kaynakları sayar (hata/kısmi/yarım kaldı)", () => {
    render(
      <SettingsSourceHealth
        query={{
          data: [
            run({ source: "a", status: "ok" }),
            run({ source: "b", status: "error" }),
            run({ source: "c", status: "partial" }),
            run({ source: "d", status: "abandoned" }),
            // Kapalı ve boş dönen kaynak "ilgi isteyen" DEĞİLDİR.
            run({ source: "e", status: "disabled" }),
            run({ source: "f", status: "empty" }),
          ],
          isLoading: false,
          isError: false,
        }}
      />,
    );
    expect(screen.getByText("3 kaynak ilgi istiyor")).toBeTruthy();
  });

  it("sorgu düştüğünde sağlıklı DEMEZ", () => {
    render(<SettingsSourceHealth query={{ data: undefined, isLoading: false, isError: true }} />);
    expect(screen.getByText(/alınamadı/)).toBeTruthy();
    expect(screen.queryByText(/sağlıklı/)).toBeNull();
    expect(healthLink()).toBe("#/health");
  });

  it("yüklenirken sahte sıfır/sağlıklı göstermez", () => {
    render(<SettingsSourceHealth query={{ data: undefined, isLoading: true, isError: false }} />);
    expect(screen.getByText("Kaynak durumu okunuyor…")).toBeTruthy();
    expect(screen.queryByText(/sağlıklı/)).toBeNull();
  });

  it("hiç koşu yoksa bunu söyler (sağlıklı demez)", () => {
    render(<SettingsSourceHealth query={{ data: [], isLoading: false, isError: false }} />);
    expect(screen.getByText("Henüz kaynak koşusu yok.")).toBeTruthy();
    expect(screen.queryByText(/sağlıklı/)).toBeNull();
  });
});
