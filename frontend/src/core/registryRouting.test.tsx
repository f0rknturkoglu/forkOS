// @vitest-environment jsdom

import { beforeAll, describe, expect, it } from "vitest";
import { moduleForPath, registerModule, titleForPath } from "./registry";

const Page = () => null;
registerModule({
  id: "dynamic-routing-test",
  title: "Medya",
  group: "track",
  routes: [
    { path: "/route-test/:id", element: Page, title: "Medya detayı" },
    { path: "/route-test", element: Page },
  ],
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
});
