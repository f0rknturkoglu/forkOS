// @vitest-environment jsdom

import { beforeAll, describe, expect, it } from "vitest";
import { allCommands, allModules, moduleForPath, navigationModules, registerModule } from "./registry";

const Page = () => null;
registerModule({
  id: "nav-hidden-test",
  title: "Gizli modül",
  group: "track",
  hidden: true,
  routes: [{ path: "/nav-hidden-test", element: Page }],
  commands: [{ id: "nav-hidden.open", label: "Gizli modülü aç", run: () => {} }],
});
registerModule({
  id: "nav-visible-test",
  title: "Görünür modül",
  group: "track",
  routes: [{ path: "/nav-visible-test", element: Page }],
});

beforeAll(() => {
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: { getItem: () => null, setItem: () => undefined, removeItem: () => undefined },
  });
});

describe("hidden modules (Faz 10)", () => {
  it("nav'da gorunmez ama kayitli kalir", () => {
    const navIds = navigationModules().map((m) => m.id);
    expect(navIds).toContain("nav-visible-test");
    expect(navIds).not.toContain("nav-hidden-test");
    expect(allModules().some((m) => m.id === "nav-hidden-test")).toBe(true);
  });

  it("rotasi cozulmeye devam eder ve komutlari palette kalir", () => {
    expect(moduleForPath("/nav-hidden-test")?.id).toBe("nav-hidden-test");
    expect(allCommands().some((c) => c.id === "nav-hidden.open")).toBe(true);
  });
});
