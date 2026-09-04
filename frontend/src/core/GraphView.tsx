/**
 * Bilgi grafi gorunumu -- second brain'in haritasi.
 *
 * Dugumler entity, kenarlar link. Yerlesim d3-force ile canli olarak oturur;
 * cizim SVG kaldigi icin etiket, tiklama, kaydirma ve yakinlastirma davranisi
 * dogrudan bizim kontrolumuzdedir.
 *
 * Etkilesim: dugumu surukle, bosluktan tut kaydir, tekerlekle yakinlastir.
 * Suruklenen dugum SABITLENIR; "Gorunumu sifirla" dugumleri yeniden salar.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type Simulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";
import { Crosshair, Maximize2, Minus, Plus } from "lucide-react";
import { api, qs } from "./api";
import { entityRoute, typeLabel } from "./entityRegistry";
import { clientToViewBox, IDENTITY, panBy, toGraph, zoomAt, type Point, type Transform } from "./graphInteraction";
import { nodeRadius } from "./graphLayout";
import { Empty, IconButton, Spinner, cx } from "./ui";
import type { KnowledgeGraph } from "./types";

const WIDTH = 900;
const HEIGHT = 560;
const VIEWBOX = { width: WIDTH, height: HEIGHT };

type GraphNode = KnowledgeGraph["nodes"][number];
type SimNode = GraphNode & SimulationNodeDatum & { r: number };
type SimLink = SimulationLinkDatum<SimNode> & KnowledgeGraph["edges"][number];
type Drag = { kind: "node"; id: string; offset: Point } | { kind: "pan"; origin: Point } | null;

export function GraphView({ focus, depth = 2 }: { focus?: string; depth?: number }) {
  const [active, setActive] = useState<string | null>(null);
  const [transform, setTransform] = useState<Transform>(IDENTITY);
  const [points, setPoints] = useState<SimNode[]>([]);
  const simulation = useRef<Simulation<SimNode, SimLink> | null>(null);
  const simulationNodes = useRef<SimNode[]>([]);
  const drag = useRef<Drag>(null);
  // SVG kosullu render ediliyor (yuklenirken/bos grafta yok). Bu yuzden ref
  // DEGIL state: element gercekten baglandiginda effect yeniden kosar.
  const [svg, setSvg] = useState<SVGSVGElement | null>(null);
  const moved = useRef(false);

  const { data, isLoading } = useQuery({
    queryKey: ["graph", focus ?? "all", depth],
    queryFn: () => api.get<KnowledgeGraph>("/graph" + qs({ focus, depth })),
  });

  const nodes = useMemo(() => data?.nodes ?? [], [data]);
  const edges = useMemo(() => data?.edges ?? [], [data]);

  // D3 nesneleri yerinde degistirir. React'e her tick'te yalnizca yeni bir
  // dizi veriyoruz; dugum nesneleri simulasyonla ayni referansta kaliyor.
  useEffect(() => {
    simulation.current?.stop();

    const nextNodes: SimNode[] = nodes.map((node, index) => {
      // Baslangic halkasi her acilista ayni; fizik buradan yumusakca oturur.
      const angle = (index / Math.max(1, nodes.length)) * Math.PI * 2;
      const radius = Math.min(WIDTH, HEIGHT) * 0.24;
      return {
        ...node,
        r: nodeRadius(node.degree),
        x: WIDTH / 2 + Math.cos(angle) * radius,
        y: HEIGHT / 2 + Math.sin(angle) * radius,
      };
    });
    const ids = new Set(nextNodes.map((node) => node.id));
    const nextLinks: SimLink[] = edges
      .filter((edge) => ids.has(edge.from) && ids.has(edge.to) && edge.from !== edge.to)
      .map((edge) => ({ ...edge, source: edge.from, target: edge.to }));

    simulationNodes.current = nextNodes;
    setPoints([...nextNodes]);
    if (nextNodes.length === 0) {
      simulation.current = null;
      return;
    }

    const nextSimulation = forceSimulation<SimNode, SimLink>(nextNodes)
      .alpha(0.95)
      // Yaklasik 3-4 saniyede durur; bos yere surekli CPU harcamaz.
      .alphaDecay(0.028)
      .velocityDecay(0.36)
      .force(
        "link",
        forceLink<SimNode, SimLink>(nextLinks)
          .id((node) => node.id)
          .distance(86)
          .strength(0.24),
      )
      .force(
        "charge",
        forceManyBody<SimNode>()
          .strength((node) => -118 - Math.min(node.degree, 12) * 5)
          .distanceMax(520),
      )
      .force(
        "collide",
        forceCollide<SimNode>()
          .radius((node) => node.r + 11)
          .strength(0.92)
          .iterations(2),
      )
      .force("x", forceX<SimNode>(WIDTH / 2).strength(0.055))
      // Tuval yatay: dikey cekim daha guclu, dugumler ustten/alttan tasmaz.
      .force("y", forceY<SimNode>(HEIGHT / 2).strength(0.085))
      .on("tick", () => setPoints([...nextNodes]));

    simulation.current = nextSimulation;
    return () => {
      nextSimulation.stop();
      if (simulation.current === nextSimulation) simulation.current = null;
    };
  }, [nodes, edges]);

  const byId = useMemo(() => new Map(points.map((point) => [point.id, point])), [points]);
  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes]);

  /** Secili dugumun komsulari -- vurgulama icin. */
  const neighbours = useMemo(() => {
    if (!active) return new Set<string>();
    const set = new Set<string>([active]);
    for (const edge of edges) {
      if (edge.from === active) set.add(edge.to);
      if (edge.to === active) set.add(edge.from);
    }
    return set;
  }, [active, edges]);
  const hovered = active ? nodeById.get(active) : undefined;

  /** Tarayici olayini viewBox koordinatina cevirir. */
  const locate = useCallback(
    (event: { clientX: number; clientY: number }): Point => {
      const rect = svg?.getBoundingClientRect();
      if (!rect) return { x: 0, y: 0 };
      return clientToViewBox({ x: event.clientX, y: event.clientY }, rect, VIEWBOX);
    },
    [svg],
  );

  const onPointerDownNode = (event: React.PointerEvent, id: string) => {
    event.stopPropagation();
    const cursor = toGraph(locate(event), transform);
    const point = byId.get(id);
    if (!point) return;
    const x = point.x ?? WIDTH / 2;
    const y = point.y ?? HEIGHT / 2;
    point.fx = x;
    point.fy = y;
    moved.current = false;
    drag.current = { kind: "node", id, offset: { x: cursor.x - x, y: cursor.y - y } };
    simulation.current?.alphaTarget(0.12).restart();
    (event.target as Element).setPointerCapture?.(event.pointerId);
  };

  const onPointerDownCanvas = (event: React.PointerEvent) => {
    moved.current = false;
    drag.current = { kind: "pan", origin: locate(event) };
    (event.currentTarget as Element).setPointerCapture?.(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent) => {
    const current = drag.current;
    if (!current) return;
    moved.current = true;
    const screen = locate(event);
    if (current.kind === "node") {
      const cursor = toGraph(screen, transform);
      const point = simulationNodes.current.find((node) => node.id === current.id);
      if (!point) return;
      point.fx = cursor.x - current.offset.x;
      point.fy = cursor.y - current.offset.y;
      point.x = point.fx;
      point.y = point.fy;
      setPoints([...simulationNodes.current]);
    } else {
      setTransform((prev) => panBy(prev, screen.x - current.origin.x, screen.y - current.origin.y));
      drag.current = { kind: "pan", origin: screen };
    }
  };

  const endDrag = () => {
    if (drag.current?.kind === "node") simulation.current?.alphaTarget(active ? 0.012 : 0);
    drag.current = null;
  };

  const activate = (id: string) => {
    setActive(id);
    if (!drag.current) simulation.current?.alphaTarget(0.012).restart();
  };

  const deactivate = () => {
    setActive(null);
    if (!drag.current) simulation.current?.alphaTarget(0);
  };

  // Tekerlek dinleyicisi ELLE baglanir: React onWheel'i passive kaydeder,
  // orada preventDefault() calismaz ve yakinlastirirken sayfa kayar.
  useEffect(() => {
    if (!svg) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      setTransform((prev) => zoomAt(prev, locate(event), event.deltaY < 0 ? 1.12 : 1 / 1.12));
    };
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  }, [svg, locate]);

  const zoomButton = (factor: number) => setTransform((prev) => zoomAt(prev, { x: WIDTH / 2, y: HEIGHT / 2 }, factor));

  const reset = () => {
    setTransform(IDENTITY);
    for (const point of simulationNodes.current) {
      point.fx = null;
      point.fy = null;
    }
    simulation.current?.alpha(0.72).alphaTarget(0).restart();
  };

  if (isLoading)
    return (
      <div className="flex h-workspace-body items-center justify-center">
        <Spinner />
      </div>
    );

  return (
    <div className="relative h-workspace-body min-h-0 overflow-hidden bg-canvas">
      {nodes.length > 0 && (
        <div className="absolute right-4 top-4 z-sticky flex items-center gap-1 rounded-overlay border border-subtle bg-surface/90 p-1 shadow-raised backdrop-blur">
          <IconButton title="Uzaklaştır" onClick={() => zoomButton(1 / 1.25)}>
            <Minus size={14} />
          </IconButton>
          <IconButton title="Yakınlaştır" onClick={() => zoomButton(1.25)}>
            <Plus size={14} />
          </IconButton>
          <IconButton title="Görünümü sıfırla" onClick={reset}>
            <Maximize2 size={14} />
          </IconButton>
        </div>
      )}
      {nodes.length === 0 ? (
        <div className="flex h-full items-center justify-center px-4">
          <Empty variant="page" title="Graf boş">
            Notlarında [[başka bir kayıt]] yazdıkça düğümler burada belirir.
          </Empty>
        </div>
      ) : (
        <>
          <svg
            ref={setSvg}
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            className={cx(
              "block h-full w-full touch-none select-none",
              drag.current ? "cursor-grabbing" : "cursor-grab",
            )}
            role="img"
            aria-label="Bilgi grafı — düğümleri sürükleyebilirsin"
            onPointerDown={onPointerDownCanvas}
            onPointerMove={onPointerMove}
            onPointerUp={endDrag}
            onPointerCancel={endDrag}
            onPointerLeave={endDrag}
          >
            {/* Tuval zemini: bosluktan tutup kaydirmak icin tiklanabilir alan. */}
            <rect x="0" y="0" width={WIDTH} height={HEIGHT} fill="transparent" />
            <g transform={`translate(${transform.x} ${transform.y}) scale(${transform.k})`}>
              {edges.map((edge, index) => {
                const a = byId.get(edge.from);
                const b = byId.get(edge.to);
                if (!a || !b) return null;
                const lit = !active || (neighbours.has(edge.from) && neighbours.has(edge.to));
                return (
                  <line
                    key={`${edge.from}-${edge.to}-${edge.relation}-${index}`}
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                    stroke="var(--text-muted)"
                    strokeWidth={lit && active ? 1.15 : 0.8}
                    opacity={lit ? (active ? 0.68 : 0.32) : 0.06}
                  />
                );
              })}
              {points.map((point) => {
                const node = nodeById.get(point.id);
                if (!node) return null;
                const lit = !active || neighbours.has(node.id);
                const x = point.x ?? WIDTH / 2;
                const y = point.y ?? HEIGHT / 2;
                return (
                  <g
                    key={node.id}
                    data-graph-node
                    data-node-id={node.id}
                    data-degree={node.degree}
                    opacity={lit ? 1 : 0.14}
                    className="cursor-pointer"
                    onPointerDown={(event) => onPointerDownNode(event, node.id)}
                    onMouseEnter={() => activate(node.id)}
                    onMouseLeave={deactivate}
                    onClick={() => {
                      // Surukleme bittiginde tiklama sayilmasin.
                      if (!moved.current) window.location.hash = entityRoute(node.type, node.id);
                    }}
                  >
                    <circle
                      cx={x}
                      cy={y}
                      r={point.r}
                      fill="var(--text-secondary)"
                      fillOpacity={active === node.id ? 1 : 0.86}
                      stroke="var(--text)"
                      strokeOpacity={node.id === data?.focus ? 0.92 : 0.18}
                      strokeWidth={node.id === data?.focus ? 2.4 : 1}
                    />
                    <title>{`${node.title} · ${typeLabel(node.type)}`}</title>
                    {(point.r >= 8 || active === node.id || node.id === data?.focus) && (
                      <text
                        x={x}
                        y={y + point.r + 11}
                        textAnchor="middle"
                        className="pointer-events-none fill-secondary text-meta"
                      >
                        {node.title.length > 24 ? `${node.title.slice(0, 23)}…` : node.title}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          </svg>

          <div className="pointer-events-none absolute bottom-4 right-4 flex items-center justify-end rounded-overlay bg-surface/80 px-3 py-2 text-meta shadow-raised backdrop-blur">
            <span className="flex items-center gap-1.5 text-muted">
              <Crosshair size={12} />
              {hovered
                ? `${hovered.title} — ${hovered.degree} bağ`
                : `${nodes.length} düğüm · ${edges.length} bağ · sürükle, yakınlaştır`}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
