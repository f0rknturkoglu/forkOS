/**
 * Bilgi grafi sayfasi -- second brain'in haritasi.
 *
 * Odak (?focus={id}) verilirse o kaydin cevresi, verilmezse tum graf.
 * Derinlik URL'de yasar ki paylasilan baglanti ayni gorunumu acsin.
 */
import { useHashRoute, navigate } from "@/app/router";
import { GraphView } from "@/core/GraphView";
import { Button, Toolbar } from "@/core/ui";

const DEPTHS = [1, 2, 3];

export function GraphPage() {
  const route = useHashRoute();
  const focus = route.params.get("focus") ?? undefined;
  const depth = Number(route.params.get("depth") ?? 2);

  const go = (next: number) =>
    navigate(`/graph?${new URLSearchParams({ ...(focus ? { focus } : {}), depth: String(next) })}`);

  return (
    <div className="relative h-workspace-body overflow-hidden bg-canvas">
      <div className="absolute left-4 top-4 z-sticky max-w-lg rounded-overlay border border-subtle bg-surface/90 px-3 py-2.5 shadow-raised backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1">
            <h1 className="text-heading text-primary">Bilgi grafı</h1>
            <p className="truncate text-meta text-muted">Notlar, görevler, kaynaklar ve aralarındaki bağlar</p>
          </div>
          {focus && (
            <Button size="sm" onClick={() => navigate("/graph")}>
              Tüm graf
            </Button>
          )}
        </div>
        {focus && (
          <Toolbar className="mt-2 border-0 bg-transparent p-0">
            <span className="text-meta text-muted">Derinlik</span>
            {DEPTHS.map((value) => (
              <Button key={value} size="sm" variant={depth === value ? "primary" : "ghost"} onClick={() => go(value)}>
                {value}
              </Button>
            ))}
          </Toolbar>
        )}
      </div>
      <GraphView focus={focus} depth={depth} />
    </div>
  );
}
