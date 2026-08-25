import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { DashboardLayout } from "./TodayPage";

describe("responsive Today layout", () => {
  it("keeps main content first in the DOM and assigns all grid areas", () => {
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
    expect(html.indexOf("merkez")).toBeLessThan(html.indexOf("sol"));
    expect(html.indexOf("sol")).toBeLessThan(html.indexOf("sağ"));
  });

  it("routes Hacker News and GitHub reads through the local API", () => {
    const source = readFileSync(new URL("./widgets/FeedStreamWidget.tsx", import.meta.url), "utf8");

    expect(source).toContain("/news/hacker-news");
    expect(source).toContain("/news/github-trending");
    expect(source).not.toContain('fetch("https://hn.algolia.com');
    expect(source).not.toContain("fetch(\n        `https://api.github.com");
  });
});
