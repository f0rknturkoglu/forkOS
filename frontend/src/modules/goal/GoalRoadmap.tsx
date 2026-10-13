import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, ChevronRight, GitBranch, Maximize2, Minus, Plus } from "lucide-react";
import { Button, Empty } from "@/core/ui";
import type { components } from "@/generated/api-schema";

type Graph = components["schemas"]["RoadmapOut"];
export type RoadmapNode = components["schemas"]["RoadmapNodeOut"];
const COLUMN = 280,
  ROW = 132,
  WIDTH = 232,
  HEIGHT = 108;

export function GoalRoadmap({
  graph,
  title,
  selected,
  onSelect,
}: {
  graph: Graph;
  title: string;
  selected: string | null;
  onSelect: (node: RoadmapNode) => void;
}) {
  const [collapsed, setCollapsed] = useState<Set<string>>(
    () => new Set(graph.nodes.filter((n) => !n.parent_id).map((n) => n.id)),
  );
  const [scale, setScale] = useState(1);
  const [list, setList] = useState(false);
  const viewport = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
  useEffect(() => {
    setCollapsed(new Set(graph.nodes.filter((n) => !n.parent_id).map((n) => n.id)));
    setScale(1);
  }, [graph.goal_id]);
  const children = useMemo(() => {
    const map = new Map<string | null, RoadmapNode[]>();
    for (const n of graph.nodes) {
      const p = n.parent_id ?? null;
      map.set(p, [...(map.get(p) ?? []), n]);
    }
    return map;
  }, [graph.nodes]);
  const layout = useMemo(() => {
    const out: { node: RoadmapNode; x: number; y: number; depth: number }[] = [];
    const seen = new Set<string>();
    const walk = (parent: string | null, depth: number) => {
      if (depth > 32) return;
      for (const node of children.get(parent) ?? []) {
        if (seen.has(node.id)) continue;
        seen.add(node.id);
        out.push({ node, x: depth * COLUMN + 24, y: out.length * ROW + 96, depth });
        if (!collapsed.has(node.id)) walk(node.id, depth + 1);
      }
    };
    walk(null, 0);
    return out;
  }, [children, collapsed]);
  const positions = new Map(layout.map((p) => [p.node.id, p]));
  const width = Math.max(560, ...layout.map((p) => p.x + WIDTH + 24));
  const height = Math.max(250, layout.length * ROW + 110);
  const toggle = (id: string) =>
    setCollapsed((old) => {
      const next = new Set(old);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const select = (node: RoadmapNode) => {
    onSelect(node);
  };
  if (!graph.nodes.length)
    return (
      <Empty title="Yol haritanı oluştur">
        <span>İlk adımını ekle veya Hermes’ten bir çalışma paketi iste.</span>
      </Empty>
    );
  return (
    <section className="rounded-card border border-subtle bg-surface overflow-hidden" aria-label="Hedef yol haritası">
      <header className="flex flex-wrap items-center gap-2 border-b border-subtle p-3">
        <h3 className="mr-auto flex items-center gap-2 text-heading">
          <GitBranch size={17} /> Yol haritası
        </h3>
        <Button size="sm" variant="ghost" onClick={() => setList(!list)}>
          {list ? "Grafik" : "Liste"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          ariaLabel="Uzaklaştır"
          onClick={() => setScale((s) => Math.max(0.3, s - 0.15))}
        >
          <Minus size={15} />
        </Button>
        <span className="text-meta tabular-nums">%{Math.round(scale * 100)}</span>
        <Button
          size="sm"
          variant="ghost"
          ariaLabel="Yakınlaştır"
          onClick={() => setScale((s) => Math.min(2, s + 0.15))}
        >
          <Plus size={15} />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            setScale(
              Math.min(
                1,
                (viewport.current?.clientWidth ?? 560) / width,
                (viewport.current?.clientHeight ?? 384) / height,
              ),
            );
            if (viewport.current) {
              viewport.current.scrollTop = 0;
              viewport.current.scrollLeft = 0;
            }
          }}
        >
          <Maximize2 size={15} /> Sığdır
        </Button>
      </header>
      {graph.truncated && (
        <p role="status" className="p-3 text-warn text-meta">
          Haritanın bir kısmı gösteriliyor; tam ilerleme hesaplanamadı.
        </p>
      )}
      {(graph.warnings ?? []).map((w, i) => (
        <p key={i} className="p-3 text-meta text-warn">
          {w}
        </p>
      ))}
      <div className={list ? "hidden" : "hidden sm:block"}>
        <div
          ref={viewport}
          tabIndex={0}
          aria-label="Grafiği kaydır; düğümler arasında ok tuşlarıyla gez"
          className="h-96 overflow-auto bg-surface-sunken cursor-grab focus-visible:outline-accent"
          onPointerDown={(e) => {
            if ((e.target as HTMLElement).closest("button")) return;
            if (!viewport.current) return;
            drag.current = {
              x: e.clientX,
              y: e.clientY,
              left: viewport.current.scrollLeft,
              top: viewport.current.scrollTop,
            };
            e.currentTarget.setPointerCapture(e.pointerId);
          }}
          onPointerMove={(e) => {
            if (drag.current && viewport.current) {
              viewport.current.scrollLeft = drag.current.left - e.clientX + drag.current.x;
              viewport.current.scrollTop = drag.current.top - e.clientY + drag.current.y;
            }
          }}
          onPointerUp={() => {
            drag.current = null;
          }}
          onPointerCancel={() => {
            drag.current = null;
          }}
        >
          <div style={{ width: width * scale, height: height * scale }}>
            <div className="relative origin-top-left" style={{ width, height, transform: `scale(${scale})` }}>
              <svg width={width} height={height} className="absolute inset-0 pointer-events-none" aria-hidden>
                <defs>
                  <marker
                    id={`arrow-${graph.goal_id}`}
                    viewBox="0 0 10 10"
                    refX="9"
                    refY="5"
                    markerWidth="6"
                    markerHeight="6"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--text-muted)" />
                  </marker>
                </defs>
                {layout.map(({ node, x, y }) => {
                  const parent = node.parent_id ? positions.get(node.parent_id) : null;
                  return parent ? (
                    <path
                      key={node.id}
                      d={`M${parent.x + WIDTH} ${parent.y + HEIGHT / 2} C${x - 24} ${parent.y + HEIGHT / 2},${x - 24} ${y + HEIGHT / 2},${x} ${y + HEIGHT / 2}`}
                      fill="none"
                      stroke="var(--border-strong)"
                      strokeWidth={2}
                      markerEnd={`url(#arrow-${graph.goal_id})`}
                    />
                  ) : (
                    <path
                      key={node.id}
                      d={`M${x + WIDTH / 2} 62 V${y}`}
                      fill="none"
                      stroke="var(--border-strong)"
                      strokeWidth={2}
                      markerEnd={`url(#arrow-${graph.goal_id})`}
                    />
                  );
                })}
                {layout.flatMap(({ node, x, y }) =>
                  (node.dependencies ?? []).map((id) => {
                    const from = positions.get(id);
                    return from ? (
                      <path
                        key={`${id}-${node.id}`}
                        d={`M${from.x + WIDTH / 2} ${from.y + HEIGHT} L${x + WIDTH / 2} ${y}`}
                        fill="none"
                        stroke="var(--accent)"
                        strokeDasharray="5 5"
                        markerEnd={`url(#arrow-${graph.goal_id})`}
                      />
                    ) : null;
                  }),
                )}
              </svg>
              <div className="absolute left-6 top-4 rounded-control bg-accent-surface px-3 py-2 text-body font-semibold">
                {title}
              </div>
              {layout.map(({ node, x, y }, i) => (
                <div
                  key={node.id}
                  style={{ left: x, top: y, width: WIDTH, height: HEIGHT }}
                  className={`absolute rounded-card border bg-surface ${selected === node.id ? "border-accent" : node.completed ? "border-ok" : node.missing ? "border-warn" : "border-subtle"}`}
                >
                  <button
                    type="button"
                    onClick={() => select(node)}
                    title={node.title}
                    className="w-full p-3 text-left focus-visible:outline-accent rounded-card"
                    aria-label={`${node.title}, ${node.percent == null ? "ilerleme bilinmiyor" : `%${node.percent}`}`}
                    onKeyDown={(e) => {
                      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                        e.preventDefault();
                        const next =
                          layout[Math.max(0, Math.min(layout.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)))];
                        const el = viewport.current?.querySelector<HTMLButtonElement>(
                          `[data-node-id="${next.node.id}"]`,
                        );
                        el?.focus();
                      }
                      if (e.key === "ArrowRight" && collapsed.has(node.id)) {
                        e.preventDefault();
                        toggle(node.id);
                      }
                      if (e.key === "ArrowLeft" && !collapsed.has(node.id)) {
                        e.preventDefault();
                        toggle(node.id);
                      }
                    }}
                    data-node-id={node.id}
                  >
                    <span className="block text-body font-medium line-clamp-2 break-words">{node.title}</span>
                    <span
                      className={`mt-1 flex items-center gap-1 text-meta ${node.completed ? "text-ok" : "text-muted"}`}
                    >
                      {node.completed && <Check size={13} />}{" "}
                      {node.percent == null
                        ? node.missing
                          ? "Bağlı kayıt bulunamıyor"
                          : "Henüz kanıt yok"
                        : `%${node.percent}`}
                    </span>
                  </button>
                  {(children.get(node.id)?.length ?? 0) > 0 && (
                    <button
                      type="button"
                      aria-expanded={!collapsed.has(node.id)}
                      aria-label={`${node.title} alt adımları`}
                      onClick={() => toggle(node.id)}
                      className="absolute bottom-1 right-2 text-secondary p-1 focus-visible:outline-accent"
                    >
                      {collapsed.has(node.id) ? <ChevronRight size={15} /> : <ChevronDown size={15} />}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
        <p className="p-3 text-meta text-muted">
          Düğüme tıkla; okla alt adımları aç. Boş alanı sürükleyerek haritayı kaydır.
        </p>
      </div>
      <div className={list ? "p-3" : "p-3 sm:hidden"}>
        <p className="mb-3 text-meta text-muted">{title} · Bağlantılı adımlar</p>
        <ul className="stack-y-2" aria-label="Yol haritası listesi">
          {layout.map(({ node, depth }) => (
            <li key={node.id} style={{ paddingInlineStart: Math.min(depth, 3) * 12 }}>
              <div className="flex gap-2 items-center">
                <Button
                  className="min-w-0 flex-1 justify-between text-left"
                  variant="ghost"
                  onClick={() => select(node)}
                >
                  <span className="break-words">{node.title}</span>
                  <span className="shrink-0 text-meta">{node.percent == null ? "—" : `%${node.percent}`}</span>
                </Button>
                {(children.get(node.id)?.length ?? 0) > 0 && (
                  <Button
                    variant="ghost"
                    ariaLabel={`${node.title} alt adımları`}
                    ariaExpanded={!collapsed.has(node.id)}
                    onClick={() => toggle(node.id)}
                  >
                    {collapsed.has(node.id) ? <ChevronRight size={15} /> : <ChevronDown size={15} />}
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
