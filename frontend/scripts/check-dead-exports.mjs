#!/usr/bin/env node
/**
 * Olu export taramasi (kural 14 yardimcisi): tanimli ama hicbir yerde import
 * edilmeyen export'ları listeler. CI esigi: varsayilan 10.
 *
 * Kullanim: node scripts/check-dead-exports.mjs [esik]
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "..", "src");
const THRESHOLD = Number(process.argv[2] ?? 10);

function walk(dir, out = [], includeTests = false) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (entry === "generated") continue;
      walk(full, out, includeTests);
    } else if (full.endsWith(".ts") || full.endsWith(".tsx")) {
      if (includeTests || !full.includes(".test.")) out.push(full);
    }
  }
  return out;
}

const files = walk(ROOT, [], false);
const contents = new Map(files.map((f) => [f, readFileSync(f, "utf8")]));
// Test dosyalari da tuketicidir (import ettikleri export'lar olu degil).
const allSource = [...contents.values(), ...walk(ROOT, [], true)
  .filter((f) => !contents.has(f)).map((f) => readFileSync(f, "utf8"))].join("\n");

// export const X / export function X / export interface X / export type X
const re = /export\s+(?:const|function|class|interface|type)\s+([A-Za-z_$][A-Za-z0-9_$]*)/g;
const dead = [];
const seen = new Set();
for (const [file, src] of contents) {
  for (const m of src.matchAll(re)) {
    const name = m[1];
    if (seen.has(name)) continue;
    seen.add(name);
    // Kendi dosyasi disinda import ediliyor mu?
    const usage = new RegExp(`\\b${name}\\b`).test(allSource.replace(src, ""));
    const imported = new RegExp(`import[^;]*\\b${name}\\b`).test(allSource.replace(src, ""));
    if (!usage || !imported) {
      dead.push(`${file.replace(ROOT + "/", "")} :: ${name}`);
    }
  }
}

dead.sort();
for (const d of dead) console.log(d);
console.error(`\nolu export: ${dead.length} (esik ${THRESHOLD})`);
if (dead.length > THRESHOLD) {
  console.error("ESIK ASILDI — olu export'lar temizlenmeli (Faz 1 kurali).");
  process.exit(1);
}
