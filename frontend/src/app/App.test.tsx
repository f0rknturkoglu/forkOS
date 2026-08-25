import { describe, expect, it } from "vitest";
import type { ModuleSpec } from "@/core/types";
import { routeForPath } from "./App";

const Index = () => null;
const Detail = () => null;
const routes: ModuleSpec["routes"] = [
  { path: "/media/:id", element: Detail },
  { path: "/media", element: Index },
];

describe("app route selection", () => {
  it("selects dynamic pages while preserving exact index routing", () => {
    expect(routeForPath(routes, "/media/media-1")?.element).toBe(Detail);
    expect(routeForPath(routes, "/media")?.element).toBe(Index);
    expect(routeForPath(routes, "/media/media-1/extra")).toBeUndefined();
  });
});
