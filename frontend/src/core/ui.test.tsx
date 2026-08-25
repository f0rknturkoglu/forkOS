import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Metric, MetricStrip, PageFrame, RowList, Section, Surface, Toolbar } from "./ui";

describe("UI primitives", () => {
  it("wraps section content in a card shell by default", () => {
    const html = renderToStaticMarkup(
      <Section title="RSS">
        <p>Akış</p>
      </Section>,
    );

    expect(html).toContain("RSS");
    expect(html).toContain("Akış");
    expect(html).toContain("rounded-card border border-subtle bg-surface");
  });

  it("drops the shell when nested inside another surface", () => {
    const html = renderToStaticMarkup(
      <Section title="RSS" flat>
        <p>Akış</p>
      </Section>,
    );

    expect(html).not.toContain("rounded-card border border-subtle bg-surface");
  });

  it("keeps explicit surfaces, metrics, toolbars, and divided rows", () => {
    const html = renderToStaticMarkup(
      <PageFrame>
        <Surface>
          <Toolbar>Filtre</Toolbar>
        </Surface>
        <MetricStrip>
          <Metric label="Açık" value={12} />
        </MetricStrip>
        <RowList>Satır</RowList>
      </PageFrame>,
    );

    expect(html).toContain("max-w-[1600px]");
    expect(html).toContain("divide-x");
    expect(html).toContain("divide-y");
  });

  it("can keep semantic list markup while using divided-row styling", () => {
    const html = renderToStaticMarkup(
      <RowList as="ul">
        <li>Birinci</li>
      </RowList>,
    );

    expect(html).toContain("<ul");
    expect(html).toContain("<li>Birinci</li>");
  });
});
