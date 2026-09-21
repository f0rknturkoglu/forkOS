import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { DashboardLayout } from "./TodayPage";

describe("responsive Today layout", () => {
  it("keeps visual and keyboard order aligned across dashboard areas", () => {
    const html = renderToStaticMarkup(
      <DashboardLayout
        hero={<span>üst kutu</span>}
        center={[<span key="center">merkez</span>]}
        left={[<span key="left">sol</span>]}
        right={[<span key="right">sağ</span>]}
      />,
    );

    expect(html).toContain("üst kutu");
    expect(html).toContain("dashboard-grid");
    expect(html).toContain("dashboard-main");
    expect(html).toContain("dashboard-left");
    expect(html).toContain("dashboard-right");
    expect(html.indexOf("sol")).toBeLessThan(html.indexOf("merkez"));
    expect(html.indexOf("merkez")).toBeLessThan(html.indexOf("sağ"));
    expect(html).toContain('aria-label="Plan"');
    expect(html).toContain('aria-label="Akış"');
  });

  it("routes Hacker News and GitHub reads through the local API", () => {
    const source = readFileSync(new URL("./widgets/FeedStreamWidget.tsx", import.meta.url), "utf8");

    expect(source).toContain("/news/hacker-news");
    expect(source).toContain("/news/github-trending");
    expect(source).not.toContain('fetch("https://hn.algolia.com');
    expect(source).not.toContain("fetch(\n        `https://api.github.com");
  });

  it("keeps the reading stream to a compact 15 items", () => {
    const source = readFileSync(new URL("./widgets/FeedStreamWidget.tsx", import.meta.url), "utf8");

    expect(source).toContain("const STREAM_LIMIT = 15");
    expect(source).toContain(".slice(0, STREAM_LIMIT)");
  });
});

describe("Home ızgara şablonu — boş sütun yer tutmaz", () => {
  const page = (columns: { left?: boolean; center?: boolean; right?: boolean }) =>
    renderToStaticMarkup(
      <DashboardLayout
        center={columns.center ? [<span key="c">merkez</span>] : []}
        left={columns.left ? [<span key="l">sol</span>] : []}
        right={columns.right ? [<span key="r">sağ</span>] : []}
      />,
    );

  it("üç sütun görünürken plan/akış/durum düzeni korunur", () => {
    const html = page({ left: true, center: true, right: true });
    expect(html).toContain("--dash-cols:300px minmax(0, 1fr) 300px");
    expect(html).toContain("--dash-areas:left main right");
    expect(html).toContain('aria-label="Akış"');
  });

  it("orta sütun gizliyken plan genişler, boş sütun hiç çizilmez", () => {
    const html = page({ left: true, right: true });
    expect(html).toContain("--dash-cols:minmax(0, 1fr) 320px");
    expect(html).toContain("--dash-areas:left right");
    expect(html).not.toContain('aria-label="Akış"');
  });

  it("durum sütunu gizliyken plan ile akış yan yana kalır", () => {
    const html = page({ left: true, center: true });
    expect(html).toContain("--dash-cols:300px minmax(0, 1fr)");
    expect(html).toContain("--dash-areas:left main");
    expect(html).not.toContain('aria-label="Durum"');
  });

  it("tek sütun kaldığında tam genişlik kullanılır", () => {
    const html = page({ left: true });
    expect(html).toContain("--dash-cols:minmax(0, 1fr)");
    expect(html).toContain("--dash-areas:left");
  });
});
