import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  Metric,
  MetricStrip,
  PageFrame,
  RowList,
  Section,
  Surface,
  Toolbar,
} from "./ui";

describe("Glance UI primitives", () => {
  it("renders section content without a default card shell", () => {
    const html = renderToStaticMarkup(
      <Section title="RSS">
        <p>Akış</p>
      </Section>,
    );

    expect(html).toContain("RSS");
    expect(html).toContain("Akış");
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
});
