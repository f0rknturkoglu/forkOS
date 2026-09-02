import { describe, expect, it } from "vitest";
import { layoutGraph, nodeRadius } from "./graphLayout";

const box = { width: 400, height: 300 };

describe("graf yerleşimi", () => {
  it("boş grafta boş döner, tek düğümü ortalar", () => {
    expect(layoutGraph([], [], box)).toEqual([]);
    const [single] = layoutGraph([{ id: "a", degree: 0 }], [], box);
    expect(single).toMatchObject({ id: "a", x: 200, y: 150 });
  });

  it("deterministik: aynı graf her seferinde aynı yerleşim", () => {
    const nodes = [
      { id: "a", degree: 2 },
      { id: "b", degree: 1 },
      { id: "c", degree: 1 },
    ];
    const edges = [
      { from: "a", to: "b" },
      { from: "a", to: "c" },
    ];
    expect(layoutGraph(nodes, edges, box)).toEqual(layoutGraph(nodes, edges, box));
  });

  it("her düğümü tuvalin içinde ve kendi yarıçapı kadar kenardan uzakta tutar", () => {
    const nodes = Array.from({ length: 24 }, (_, i) => ({ id: `n${i}`, degree: i % 5 }));
    const edges = nodes.slice(1).map((node, i) => ({ from: nodes[i].id, to: node.id }));
    for (const point of layoutGraph(nodes, edges, box)) {
      expect(point.x).toBeGreaterThanOrEqual(point.r);
      expect(point.x).toBeLessThanOrEqual(box.width - point.r);
      expect(point.y).toBeGreaterThanOrEqual(point.r);
      expect(point.y).toBeLessThanOrEqual(box.height - point.r);
    }
  });

  it("bilinmeyen uçlu kenar yerleşimi bozmaz", () => {
    const placed = layoutGraph(
      [
        { id: "a", degree: 0 },
        { id: "b", degree: 0 },
      ],
      [{ from: "a", to: "yok" }],
      box,
    );
    expect(placed).toHaveLength(2);
    expect(placed.every((p) => Number.isFinite(p.x) && Number.isFinite(p.y))).toBe(true);
  });

  it("yarıçap bağ sayısıyla büyür ama tavanı aşmaz", () => {
    expect(nodeRadius(0)).toBeLessThan(nodeRadius(9));
    expect(nodeRadius(10_000)).toBeLessThanOrEqual(16);
  });
});

describe("yerleşim kalitesi", () => {
  /** Gercek grafa benzer: bir yildiz, bir zincir, bir de kopuk cift. */
  const nodes = Array.from({ length: 14 }, (_, i) => ({ id: `n${i}`, degree: 1 }));
  const edges = [
    ...[1, 2, 3, 4, 5].map((i) => ({ from: "n0", to: `n${i}` })),
    ...[7, 8, 9, 10, 11, 12].map((i) => ({ from: `n${i - 1}`, to: `n${i}` })),
    { from: "n13", to: "n6" },
  ];
  const canvas = { width: 860, height: 520 };

  it("düğümleri kenara yapıştırmaz", () => {
    // Regresyon: kuvvetler dengesizken butun kume alt kenara diziliyordu.
    const placed = layoutGraph(nodes, edges, canvas);
    const stuck = placed.filter(
      (p) => p.x <= p.r + 6 || p.x >= canvas.width - p.r - 6 || p.y <= p.r + 6 || p.y >= canvas.height - p.r - 6,
    );
    expect(stuck.length).toBeLessThanOrEqual(2);
  });

  it("tuvalin dikey alanını gerçekten kullanır", () => {
    const ys = layoutGraph(nodes, edges, canvas).map((p) => p.y);
    const spread = Math.max(...ys) - Math.min(...ys);
    // Hepsi tek bir yatay serite dizilmis olmamali.
    expect(spread).toBeGreaterThan(canvas.height * 0.35);
  });

  it("bağlı düğümleri bağsızlardan daha yakın tutar", () => {
    const placed = layoutGraph(nodes, edges, canvas);
    const at = new Map(placed.map((p) => [p.id, p]));
    const gap = (a: string, b: string) => Math.hypot(at.get(a)!.x - at.get(b)!.x, at.get(a)!.y - at.get(b)!.y);
    const linked = edges.map((e) => gap(e.from, e.to)).reduce((s, v) => s + v, 0) / edges.length;
    // "n0" yildizin merkezi; "n13" bambaska bir kumede.
    expect(linked).toBeLessThan(gap("n0", "n13"));
  });
});
