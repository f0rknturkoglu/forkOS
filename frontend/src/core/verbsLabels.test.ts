/**
 * Guard: akis satirlari HAM fiil anahtari gostermez.
 *
 * Kanonik fiil defteri backend'dedir (core/registry.py CORE_EVENT_VERBS +
 * her modulun event_verbs listesi). Etiket sozlugu ise burada, insan dilinde
 * durur. Ikisi ayrisirsa kullanici `opportunity.source_status_changed` gibi
 * bir anahtar okur -- bu test o ayrisimi yakalar.
 */

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { VERB_LABELS, describe as describeEvent, verbTitle } from "./verbs";

const BACKEND = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..", "backend");

/** Parantez/koseli parantez dengesini sayarak `event_verbs=[...]` blogunu ceker. */
function blockAt(source: string, openIndex: number): string {
  const open = source[openIndex];
  const close = open === "[" ? "]" : ")";
  let depth = 0;
  for (let i = openIndex; i < source.length; i += 1) {
    if (source[i] === open) depth += 1;
    else if (source[i] === close) {
      depth -= 1;
      if (depth === 0) return source.slice(openIndex, i + 1);
    }
  }
  throw new Error(`kapanmayan blok: ${openIndex}`);
}

function quotedVerbs(block: string): string[] {
  return [...block.matchAll(/"([^"]+)"/g)].map((m) => m[1]);
}

/** backend/app/core/registry.py + app/modules/<mod>/__init__.py -> kanonik fiiller. */
function canonicalVerbs(): string[] {
  const registry = readFileSync(join(BACKEND, "app", "core", "registry.py"), "utf8");
  const coreStart = registry.indexOf("CORE_EVENT_VERBS");
  expect(coreStart).toBeGreaterThan(-1); // defter tasinirsa test sessizce bos donmesin
  const verbs = quotedVerbs(blockAt(registry, registry.indexOf("(", coreStart)));

  const modulesDir = join(BACKEND, "app", "modules");
  for (const entry of readdirSync(modulesDir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const init = join(modulesDir, entry.name, "__init__.py");
    if (!existsSync(init)) continue;
    const source = readFileSync(init, "utf8");
    for (const match of source.matchAll(/event_verbs\s*=\s*([[(])/g)) {
      const openIndex = (match.index ?? 0) + match[0].length - 1;
      verbs.push(...quotedVerbs(blockAt(source, openIndex)));
    }
  }
  return verbs;
}

const CANONICAL = canonicalVerbs();

/**
 * Defterde OLMAYAN ama gercek `event` tablosunda duran fiiller: modul
 * kaldirildi, tablo append-only oldugu icin gecmis satirlar hala akista
 * gorunur. Etiketleri silinirse eski kayitlar ham anahtara duser.
 */
const LEGACY_IN_DATA = ["habit.checked", "habit.deleted", "book.deleted", "media.status_changed"];

describe("kanonik fiil defteri kapsamasi", () => {
  it("defter okunur (bos kume uzerinde bos yere gecmez)", () => {
    expect(CANONICAL.length).toBeGreaterThan(100);
    expect(new Set(CANONICAL).size).toBe(CANONICAL.length); // ayni fiil iki kez yazilmasin
  });

  it("her kanonik fiilin Turkce etiketi var", () => {
    const missing = CANONICAL.filter((verb) => !VERB_LABELS[verb]);
    expect(missing).toEqual([]);
  });

  it("gercek veride kalan eski fiiller de etiketli", () => {
    expect(LEGACY_IN_DATA.filter((verb) => !VERB_LABELS[verb])).toEqual([]);
  });

  it("etiketler ham anahtar degil: nokta ve alt cizgi tasimaz", () => {
    const raw = Object.entries(VERB_LABELS)
      .filter(([, label]) => label.includes(".") || label.includes("_"))
      .map(([verb]) => verb);
    expect(raw).toEqual([]);
  });
});

describe("etiketsiz fiil davranisi", () => {
  it("describe okunur yedege cevirir, ham anahtari gostermez", () => {
    expect(describeEvent("bilinmeyen.fiil", {})).toBe("Fiil");
    expect(describeEvent("media.brand_new_verb", { title: "Dizi" })).toBe("Brand new verb — Dizi");
  });

  it("verbTitle ham anahtari tooltip icin korur", () => {
    expect(verbTitle("media.brand_new_verb")).toBe("media.brand_new_verb");
    expect(verbTitle("todo.completed")).toBe("Görev tamamlandı · todo.completed");
  });
});
