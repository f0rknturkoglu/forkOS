import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { ReactNode } from "react";
import { HomeRegions } from "./TodayPage";
import type { TodayRegion } from "@/core/types";

/**
 * Home bölge yerleşimi (Polish 1 §13-§19).
 *
 * Eski "Plan / Akış / Durum" üç sütun modeli kaldırıldı: boş bölge ne çizilir
 * ne yer tutar. Bu testler bölge modelinin sözleşmesini sabitler.
 */

const surface = (label: string) => [<span key={label}>{label}</span>];

function regions(parts: Partial<Record<TodayRegion, ReactNode[]>>) {
  return {
    priority: parts.priority ?? [],
    main: parts.main ?? [],
    rail: parts.rail ?? [],
    secondary: parts.secondary ?? [],
  };
}

const page = (parts: Partial<Record<TodayRegion, ReactNode[]>>) =>
  renderToStaticMarkup(<HomeRegions byRegion={regions(parts)} />);

describe("Home bölgeleri", () => {
  it("priority bölgesi main'den önce ve tam genişlikte gelir", () => {
    const html = page({ priority: surface("karar"), main: surface("plan"), rail: surface("dikkat") });
    expect(html.indexOf("karar")).toBeLessThan(html.indexOf("plan"));
    expect(html).toContain("home-priority");
    expect(html).toContain('aria-label="Karar bekleyen"');
  });

  it("priority boşsa hiç çizilmez (boşluk bırakmaz)", () => {
    const html = page({ main: surface("plan"), rail: surface("dikkat") });
    expect(html).not.toContain("home-priority");
    expect(html).not.toContain("Karar bekleyen");
  });

  it("main + rail yan yana ızgarada; rail dar", () => {
    const html = page({ main: surface("şimdi"), rail: surface("dikkat") });
    expect(html).toContain("--home-cols:minmax(0, 1fr) minmax(280px, 340px)");
    expect(html).toContain('aria-label="Gün"');
    expect(html).toContain('aria-label="Dikkat"');
  });

  it("rail boşsa main tam genişliğe yayılır (boş sütun tutulmaz)", () => {
    const html = page({ main: surface("şimdi") });
    expect(html).toContain("--home-cols:minmax(0, 1fr)");
    expect(html).not.toContain("home-rail");
    expect(html).not.toContain("home-split".replace("home-split", 'aria-label="Dikkat"'));
  });

  it("main boşsa rail tek başına çizilir", () => {
    const html = page({ rail: surface("dikkat") });
    expect(html).not.toContain("home-main");
    expect(html).toContain("home-rail");
  });

  it("ikincil yüzeyler main/rail'in ALTINDA gelir", () => {
    const html = page({ main: surface("plan"), secondary: surface("akış") });
    expect(html.indexOf("plan")).toBeLessThan(html.indexOf("akış"));
    expect(html).toContain('aria-label="Bağlamsal"');
  });

  it("ikincil bölge boşsa çizilmez: orta delik oluşmaz", () => {
    const html = page({ main: surface("plan"), rail: surface("dikkat") });
    expect(html).not.toContain("home-secondary");
    expect(html).not.toContain("Bağlamsal");
  });

  it("tek bölge doluyken bölge etiketi gösterilmez", () => {
    const html = page({ main: surface("plan") });
    expect(html).not.toContain('class="label-caps');
  });

  it("bölge etiketleri yalnız birden fazla bölge doluyken görünür", () => {
    const html = page({ main: surface("plan"), rail: surface("dikkat") });
    expect(html).toContain("label-caps");
  });
});

describe("Home düzeni CSS sözleşmesi", () => {
  const css = readFileSync(new URL("../../index.css", import.meta.url), "utf8");

  it("eski üç sütun dashboard kuralları kaldırıldı", () => {
    expect(css).not.toContain(".dashboard-grid");
    expect(css).not.toContain(".dashboard-left");
    expect(css).not.toContain('grid-template-areas: "left main right"');
  });

  it("bölge ızgarası içerikten türeyen şablonu kullanır", () => {
    expect(css).toContain(".home-regions");
    expect(css).toContain("var(--home-cols");
    expect(css).toContain(".home-secondary");
  });

  it("mobilde tek sütun, geniş ekranda çok sütun", () => {
    expect(css).toMatch(/\.home-split\s*\{[^}]*grid-template-columns: minmax\(0, 1fr\);/s);
    expect(css).toContain("min-width: 1024px");
    expect(css).toContain("min-width: 768px");
  });
});
