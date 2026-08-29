import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { OpportunityCollection } from "./OpportunityList";

describe("opportunity responsive collection", () => {
  it("keeps rows one-dimensional", () => {
    const html = renderToStaticMarkup(
      <OpportunityCollection layout="rows"><article>row</article></OpportunityCollection>,
    );
    expect(html).toContain("divide-y");
    expect(html).not.toContain("grid-cols-3");
  });
});
