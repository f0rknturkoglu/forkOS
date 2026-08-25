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

const MODULES_ROOT = resolve(__dirname, "..", "modules");

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) walk(full, out);
    else if (full.endsWith(".tsx") && !full.endsWith(".test.tsx")) out.push(full);
  }
  return out;
}

const files = walk(MODULES_ROOT);

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
