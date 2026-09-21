// @vitest-environment jsdom
/**
 * Faz 12: study + learning tek modul. Eski /study rotasi hala cozuluyor
 * (kurlma yok), modul kaydi tekil ve nav'da tek giris var.
 */
import { beforeAll, describe, expect, it } from "vitest";
import { allModules, moduleForPath } from "./registry";
import "./../modules/learning/index";

beforeAll(() => {
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: { getItem: () => null, setItem: () => undefined, removeItem: () => undefined },
  });
});

describe("birlesik ogrenme modulu (Faz 12)", () => {
  it("tek modul kaydi: /learning ve /study ayni module gider", () => {
    const modules = allModules().filter((m) => m.id === "learning");
    expect(modules).toHaveLength(1);
    expect(moduleForPath("/learning")?.id).toBe("learning");
    expect(moduleForPath("/study")?.id).toBe("learning");
    // Eski study modulu ayri bir nav girisini artik tutmuyor.
    expect(allModules().some((module) => module.id === "study")).toBe(false);
  });
});
