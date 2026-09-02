import { describe, expect, it } from "vitest";
import {
  clampZoom,
  clientToViewBox,
  IDENTITY,
  MAX_ZOOM,
  MIN_ZOOM,
  panBy,
  toGraph,
  toScreen,
  zoomAt,
} from "./graphInteraction";

describe("zoom", () => {
  it("ölçeği sınırlar içinde tutar", () => {
    expect(clampZoom(100)).toBe(MAX_ZOOM);
    expect(clampZoom(0.001)).toBe(MIN_ZOOM);
    expect(clampZoom(Number.NaN)).toBe(1);
  });

  it("imlecin altındaki noktayı yerinde tutar", () => {
    const anchor = { x: 320, y: 180 };
    const next = zoomAt(IDENTITY, anchor, 1.6);
    // Yakinlastirmadan once ve sonra ayni graf noktasi imlecin altinda olmali.
    const before = toGraph(anchor, IDENTITY);
    const after = toGraph(anchor, next);
    expect(after.x).toBeCloseTo(before.x, 6);
    expect(after.y).toBeCloseTo(before.y, 6);
  });

  it("tavana dayanınca kaydırmayı da bozmaz", () => {
    const zoomed = { x: 10, y: 20, k: MAX_ZOOM };
    expect(zoomAt(zoomed, { x: 100, y: 100 }, 2)).toEqual(zoomed);
  });
});

describe("koordinat çevrimi", () => {
  it("ekran ve graf koordinatları birbirinin tersi", () => {
    const transform = { x: -120, y: 45, k: 1.75 };
    const point = { x: 233, y: 411 };
    const round = toScreen(toGraph(point, transform), transform);
    expect(round.x).toBeCloseTo(point.x, 6);
    expect(round.y).toBeCloseTo(point.y, 6);
  });

  it("kaydırma her iki ekseni de taşır", () => {
    expect(panBy({ x: 5, y: 5, k: 2 }, 10, -3)).toEqual({ x: 15, y: 2, k: 2 });
  });
});

describe("tarayıcı → viewBox", () => {
  it("CSS ölçeğini hesaba katar", () => {
    // SVG 430px genislikte gosteriliyor ama viewBox 860 -- oran 2.
    const rect = { left: 30, top: 10, width: 430, height: 260 };
    const viewBox = { width: 860, height: 520 };
    expect(clientToViewBox({ x: 30, y: 10 }, rect, viewBox)).toEqual({ x: 0, y: 0 });
    expect(clientToViewBox({ x: 245, y: 140 }, rect, viewBox)).toEqual({ x: 430, y: 260 });
  });

  it("ölçülmemiş (sıfır boyutlu) kutuda çökmez", () => {
    const zero = { left: 0, top: 0, width: 0, height: 0 };
    expect(clientToViewBox({ x: 12, y: 8 }, zero, { width: 800, height: 500 })).toEqual({ x: 12, y: 8 });
  });
});
