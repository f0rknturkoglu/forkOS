// @vitest-environment jsdom

import { beforeAll, describe, expect, it } from "vitest";
import { moduleForPath, registerModule, titleForPath } from "./registry";

const Page = () => null;
registerModule({
  id: "dynamic-routing-test",
  title: "Medya",
  routes: [
    { path: "/route-test/:id", element: Page, title: "Medya detayı" },
    { path: "/route-test", element: Page },
  ],
});
registerModule({
  id: "static-routing-test",
  title: "İstatistikler",
  routes: [{ path: "/route-test/stats", element: Page, title: "Statik istatistik" }],
});

beforeAll(() => {
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: { getItem: () => null, setItem: () => undefined, removeItem: () => undefined },
  });
});

describe("registry dynamic routing", () => {
  it("keeps dynamic pages owned and titled by their registered module", () => {
    expect(moduleForPath("/route-test/media-1")?.id).toBe("dynamic-routing-test");
    expect(titleForPath("/route-test/media-1")).toBe("Medya detayı");
    expect(moduleForPath("/route-test")?.id).toBe("dynamic-routing-test");
  });

  it("prefers a later exact static route for ownership and title", () => {
    expect(moduleForPath("/route-test/stats")?.id).toBe("static-routing-test");
    expect(titleForPath("/route-test/stats")).toBe("Statik istatistik");
  });
});
