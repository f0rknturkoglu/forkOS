/**
 * Kural 14 guardrail'i: mutation sonrasi tazeleme invalidateAfter() ile yapilir;
 * ham invalidate("a","b") ve ham invalidateQueries({ ... }) modul/core dosyalarinda yasak.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { AFTER } from "./invalidation";

const ROOT = resolve(__dirname, "..");

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) walk(full, out);
    else if (full.endsWith(".ts") || full.endsWith(".tsx")) {
      if (!full.endsWith(".test.ts") && !full.endsWith(".test.tsx") && !full.includes("__snapshots__")) {
        out.push(full);
      }
    }
  }
  return out;
}

// invalidation.ts ve queryClient.ts tanim dosyalaridir; kendi yorumlarinda
// "invalidate(a,b)" ornegi gecer (kural 14 cagri yerlerini baglar).
const EXEMPT = new Set([join(ROOT, "core", "invalidation.ts"), join(ROOT, "core", "queryClient.ts")]);
const files = walk(join(ROOT, "modules"))
  .concat(walk(join(ROOT, "core")))
  .filter((f) => !EXEMPT.has(f));

describe("merkezi invalidation (kural 14)", () => {
  it("modul ve core dosyalarinda ham invalidate( cagrisi kullanmaz", () => {
    const hits = files.filter((f) => {
      const src = readFileSync(f, "utf8");
      // tanim ve yorum haric: cagri formu invalidate("...
      return /[^A-Za-z]invalidate\(\s*["']/.test(src);
    });
    expect(hits).toEqual([]);
  });

  it("modul ve core dosyalarinda ham invalidateQueries({ cagrisi kullanmaz", () => {
    const hits = files.filter((f) => /invalidateQueries\(\s*\{/.test(readFileSync(f, "utf8")));
    expect(hits).toEqual([]);
  });

  it("AFTER haritasi tanimli her olayin tazeleme anahtari var", () => {
    for (const [event, keys] of Object.entries(AFTER)) {
      expect(keys.length, `${event} en az bir anahtar`).toBeGreaterThan(0);
      expect(keys, `${event} anahtarlari benzersiz`).toEqual([...new Set(keys)]);
    }
  });

  it("bugun-agenda her yazma olayinda tazeleniyor", () => {
    for (const event of [
      "todo.write",
      "plan.write",
      "rss.write",
      "opportunity.write",
      "project.write",
      "calendar.write",
    ]) {
      expect(AFTER[event as keyof typeof AFTER], `${event} bugun-agenda icermeli`).toContain("today-agenda");
    }
  });

  it("kariyer onayı kanonik öğrenme ve hedef özetlerini tazeler", () => {
    expect(AFTER["career-strategy.write"]).toEqual(
      expect.arrayContaining([
        "study-tree",
        "study-areas",
        "study-review",
        "study-stale",
        "today-agenda",
        "strategy-overview",
        "career-goal",
      ]),
    );
  });

  it("plan yazinca gorevler sayfasi da tazeleniyor (Faz 9)", () => {
    expect(AFTER["plan.write"]).toContain("todos");
  });
});
