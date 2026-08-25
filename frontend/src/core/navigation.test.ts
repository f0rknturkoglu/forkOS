import { describe, expect, it } from "vitest";
import type { ModuleSpec } from "./types";
import {
  activeNavigationGroup,
  groupTarget,
  navigationGroups,
} from "./navigation";

const Page = () => null;
const modules: ModuleSpec[] = [
  {
    id: "today",
    title: "Bugün",
    group: "pinned",
    routes: [{ path: "/", element: Page }],
  },
  {
    id: "rss",
    title: "RSS",
    group: "capture",
    routes: [{ path: "/rss", element: Page }],
  },
  {
    id: "opportunity",
    title: "Fırsatlar",
    group: "track",
    routes: [
      { path: "/opportunities", element: Page },
      { path: "/sources", element: Page },
    ],
  },
  {
    id: "media",
    title: "Medya",
    group: "track",
    routes: [
      { path: "/media/:id", element: Page },
      { path: "/media", element: Page },
    ],
  },
];

describe("navigation model", () => {
  const groups = navigationGroups(modules);

  it("derives the active group from secondary routes", () => {
    expect(activeNavigationGroup("/sources", groups).id).toBe("track");
  });

  it("uses the first module route as group target", () => {
    expect(groupTarget(groups.find((group) => group.id === "capture")!)).toBe("/rss");
  });

  it("shows only the active group's modules in secondary navigation", () => {
    const active = activeNavigationGroup("/sources", groups);
    expect(active.modules.map((module) => module.id)).toEqual(["opportunity", "media"]);
  });

  it("keeps a dynamic detail in its module group and targets the concrete index", () => {
    const active = activeNavigationGroup("/media/media-1", groups);
    expect(active.id).toBe("track");
    expect(groupTarget(active)).toBe("/opportunities");
  });

  it("prefers a static route's group over an earlier dynamic match", () => {
    const competing = navigationGroups([
      modules[0],
      { id: "dynamic", title: "Dinamik", group: "capture", routes: [{ path: "/media/:id", element: Page }] },
      { id: "stats", title: "İstatistik", group: "system", routes: [{ path: "/media/stats", element: Page }] },
    ]);
    expect(activeNavigationGroup("/media/stats", competing).id).toBe("system");
  });
});
