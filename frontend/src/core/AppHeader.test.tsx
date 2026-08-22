import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { ModuleSpec } from "./types";
import { navigationGroups } from "./navigation";
import { NavigationRows } from "./AppHeader";

const Page = () => null;
const modules: ModuleSpec[] = [
  { id: "today", title: "Bugün", group: "pinned", routes: [{ path: "/", element: Page }] },
  { id: "rss", title: "RSS", group: "capture", routes: [{ path: "/rss", element: Page }] },
  { id: "todo", title: "Görevler", group: "do", routes: [{ path: "/todos", element: Page }] },
];

describe("two-level app header", () => {
  it("keeps group and module navigation in separate labelled rows", () => {
    const html = renderToStaticMarkup(
      <NavigationRows
        path="/rss"
        groups={navigationGroups(modules)}
        utilities={<span>araçlar</span>}
      />,
    );

    expect(html).toContain('aria-label="Ana bölümler"');
    expect(html).toContain('aria-label="Modüller"');
    expect(html).toContain('href="#/rss"');
    expect(html).toContain("RSS");
    expect(html).toContain("araçlar");
  });
});
