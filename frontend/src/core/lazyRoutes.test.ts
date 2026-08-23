import { describe, expect, it } from "vitest";

import "@/modules";
import { allRoutes } from "./registry";

describe("module routes", () => {
  it("registers every page as a React lazy component", () => {
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: { getItem: () => null },
    });
    const routes = allRoutes();

    expect(routes.length).toBeGreaterThan(10);
    for (const route of routes) {
      const lazyType = route.element as typeof route.element & { $$typeof?: symbol };
      expect(lazyType.$$typeof, route.path).toBe(Symbol.for("react.lazy"));
    }
  });
});
