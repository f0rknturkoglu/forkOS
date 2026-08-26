/**
 * Tasarim sistemi guardrail'i — modul kodu tokenlari es gecemesin.
 *
 * Tarama alani: src/modules alti .tsx dosyalari (test haric). core/ bu taramanin
 * DISINDADIR:
 * ui.tsx primitivelerin kendisidir, orada ham etiket/token tanimlanir.
 *
 * Yasaklanan desenler (docs/faz0-kararlar.md Faz 2 kararlari):
 *   - keyfi tipografi (olcek disi boyut siniflari) -> tailwind fontSize adimlari
 *   - #RRGGBB          -> JSX'te sabit hex; renk tokenlardan gelir (--chart-*, --kind-*)
 *   - <input/select/textarea> -> ham kontroller; Input/Select/Textarea/Checkbox/Range/NumberInput
 *   - rounded-md/lg/xl/2xl -> yaricap tokenlari: rounded-control/card/overlay
 *   - bg-blue-500 gibi ham tailwind palet siniflari -> semantik siniflar
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";
// @ts-expect-error tailwind.config.js bir JS dosyasi; declaration uretilmiyor.
import tailwindConfig from "../../tailwind.config.js";

const MODULES_ROOT = resolve(__dirname, "..", "modules");
const SRC_ROOT = resolve(__dirname, "..");

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) walk(full, out);
    else if (full.endsWith(".tsx") && !full.endsWith(".test.tsx")) out.push(full);
  }
  return out;
}

/** Fixture'siz tam src taramasi: modules (walk) + core ve diger kok klasorler.
 *  Test fixture'lari kendi yasak orneklerini tasirlar (bg-blue-500 vb.), o
 *  yuzden *.test.* disarida. */
function walkDir(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) walkDir(full, out);
    else if (
      (full.endsWith(".ts") || full.endsWith(".tsx")) &&
      !full.endsWith(".test.ts") &&
      !full.endsWith(".test.tsx")
    )
      out.push(full);
  }
  return out;
}

const files = walk(MODULES_ROOT);
const allSourceFiles = files.concat(walkDir(join(SRC_ROOT, "core")));

/** Ham tailwind palet sinifi: bg-blue-500, text-gray-400, border-red-200 ... */
const RAW_PALETTE =
  /(?:^|["'\s`])(?:bg|text|border|ring|from|to|via|fill|stroke|divide|shadow)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b/;

describe("tasarım sistemi (modüller)", () => {
  it("keyfi tipografi (olcek disi boyut) kullanmaz", () => {
    const pattern = "text-" + "\\[\\d"; // literal "text-[\d"; tailwind taramasin diye parcali
    const hits = files.filter((f) => new RegExp(pattern).test(readFileSync(f, "utf8")));
    expect(hits).toEqual([]);
  });

  it("JSX'te sabit hex (#RRGGBB) kullanmaz", () => {
    const hits = files.filter((f) => /#[0-9a-fA-F]{6}/.test(readFileSync(f, "utf8")));
    expect(hits).toEqual([]);
  });

  it("ham <input>/<select>/<textarea> kullanmaz", () => {
    const hits = files.filter((f) => /<(input|select|textarea)\b/.test(readFileSync(f, "utf8")));
    expect(hits).toEqual([]);
  });

  it("yariçap tokenı yerine rounded-md/lg/xl/2xl kullanmaz", () => {
    const hits = files.filter((f) => /\brounded-(?:md|lg|xl|2xl)\b/.test(readFileSync(f, "utf8")));
    expect(hits).toEqual([]);
  });

  it("ham tailwind palet sınıfı (bg-blue-500 vb.) kullanmaz", () => {
    const hits = files.filter((f) => RAW_PALETTE.test(readFileSync(f, "utf8")));
    expect(hits).toEqual([]);
  });
});

/**
 * Faz 8 guardrail'i — "tanimli token sinifi gercekten cozuluyor mu".
 * Heatmap regresyonu (tailwind.config.js'ten heat grubu silinmis, STEP_BG
 * siniflari uretilmiyordu) bu test olmadan sessizce gecti.
 *
 * SINIR: string birlesik kurulan siniflar (bg-heat-${n}) yakalanamaz; moduller
 * literal sinif dizisi kullanmali (Heatmap STEP_BG gibi).
 */
const colors = tailwindConfig.theme.extend.colors;
const COLOR_PREFIX = "(?:bg|text|border|ring|fill|stroke)";
const COLOR_CLASS = new RegExp(`\\b${COLOR_PREFIX}-([a-z]+)-([a-z0-9]+)\\b`, "g");

/** Renk degil ama iki parcali gorunen siniflar: border yon kalinligi
 *  (border-t-2), ring-offset, gradient, clip, tipografi olcegi adlari. */
const NON_COLOR_GROUPS = new Set([
  "t",
  "b",
  "l",
  "r",
  "x",
  "y",
  "offset",
  "gradient",
  "clip",
  "no",
  "numeral",
  "display",
  "shadow",
  "divide",
  "space",
]);

describe("token cozumleme (Faz 8)", () => {
  it("src'te kullanilan her renk sinifi tailwind.config.js'te tanimli", () => {
    const missing: string[] = [];
    for (const file of allSourceFiles) {
      const body = readFileSync(file, "utf8");
      for (const m of body.matchAll(COLOR_CLASS)) {
        const group = m[1];
        const tone = m[2];
        const def = colors[group];
        if (typeof def === "object") {
          if (!(tone in def)) missing.push(`${m[0]}  (${file.replace(SRC_ROOT, "src")})`);
        } else if (!NON_COLOR_GROUPS.has(group)) {
          missing.push(`${m[0]}  (${file.replace(SRC_ROOT, "src")})`);
        }
      }
    }
    expect(missing).toEqual([]);
  });

  it("config'teki alt-tonlu renk gruplarinin tamami src'te kullaniliyor (esik 0)", () => {
    const used = new Set<string>();
    for (const file of allSourceFiles) {
      const body = readFileSync(file, "utf8");
      for (const m of body.matchAll(COLOR_CLASS)) used.add(m[1]);
    }
    const unused = Object.entries(colors)
      .filter(([, v]) => typeof v === "object")
      .map(([g]) => g)
      .filter((g) => !used.has(g));
    expect(unused).toEqual([]);
  });
});
