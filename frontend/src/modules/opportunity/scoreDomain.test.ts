import { describe, expect, it } from "vitest";
import { PROFILE_MATCH_PRESETS, SCORE_PRESETS } from "./filterState";
import { SCORE_CAP, SCORE_FLOOR, scoreBand } from "./scoreDomain";

describe("score domain", () => {
  it("preset aralıkları evreni boşluksuz ve çakışmasız kaplar", () => {
    const ranges = SCORE_PRESETS.filter((preset) => preset.min !== undefined);
    // Domain: elenmiş (-1) + 0..100 (iki ondalık adımlarla).
    const values = [SCORE_FLOOR, ...Array.from({ length: SCORE_CAP * 100 + 1 }, (_, i) => i / 100)];
    for (const value of values) {
      const hits = ranges.filter(
        (preset) => value >= (preset.min ?? 0) && value <= (preset.max ?? SCORE_CAP),
      );
      expect(hits, `değer ${value} tam olarak bir aralığa girmeli`).toHaveLength(1);
    }
  });

  it("profil uyumu presetleri de boşluksuz ve çakışmasız", () => {
    const ranges = PROFILE_MATCH_PRESETS.filter(
      (preset) => preset.min !== undefined || preset.state !== undefined,
    );
    for (let step = 0; step <= 100; step += 1) {
      const value = step / 100;
      const hits = ranges.filter(
        (preset) =>
          preset.state === undefined &&
          value >= (preset.min ?? 0) &&
          value <= (preset.max ?? 1),
      );
      expect(hits, `oran ${value} tam olarak bir preset'e girmeli`).toHaveLength(1);
    }
  });

  it("hesaplanmamış skor ile 0 ve elenmiş skoru ayırır", () => {
    expect(scoreBand(null)).toBe("unknown");
    expect(scoreBand(undefined)).toBe("unknown");
    expect(scoreBand(0)).toBe("low");
    expect(scoreBand(-1)).toBe("eliminated");
    expect(scoreBand(39.99)).toBe("low");
    expect(scoreBand(40)).toBe("fair");
    expect(scoreBand(69.99)).toBe("fair");
    expect(scoreBand(70)).toBe("strong");
    expect(scoreBand(100)).toBe("strong");
  });
});
