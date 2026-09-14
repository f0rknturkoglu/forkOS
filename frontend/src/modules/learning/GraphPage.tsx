/**
 * Bilgi grafi sayfasi -- second brain'in haritasi.
 *
 * Odak (?focus={id}) verilirse o kaydin cevresi, verilmezse tum graf.
 * Derinlik de URL'de yasar ki paylasilan baglanti ayni gorunumu acsin.
 *
 * Ogrenmeden gelindiginde odak KORUNUR: "Ogrenmeye don" bagi
 * `#/learning?focus=<id>` adresine gider, yani sayfa ayni konuyla acilir.
 * "Tum graf" ise odagi birakir (paylasilabilir genel gorunum).
 */
import { ArrowLeft } from "lucide-react";
import { GraphView } from "@/core/GraphView";
import { Button, Toolbar } from "@/core/ui";
import { navigate, useHashRoute } from "@/app/router";

const DEPTHS = [1, 2, 3];

export function GraphPage() {
  const route = useHashRoute();
  const focus = route.params.get("focus") ?? undefined;
  const fromNotes = route.params.get("from") === "notes";
  const requested = Number(route.params.get("depth") ?? 2);
  // Bozuk/elle yazilmis derinlik grafigi NaN ile cizmesin.
  const depth = DEPTHS.includes(requested) ? requested : 2;

  const go = (next: number) =>
    navigate(
      `/graph?${new URLSearchParams({ ...(focus ? { focus } : {}), ...(fromNotes ? { from: "notes" } : {}), depth: String(next) })}`,
    );

  // Secili konu geri donuste korunur: LF1 `?focus=` ile ayni konuyu acar.
  const backHref = fromNotes
    ? focus
      ? `#/notes?focus=${encodeURIComponent(focus)}`
      : "#/notes"
    : focus
      ? `#/learning?focus=${encodeURIComponent(focus)}`
      : "#/learning";

  return (
    <div className="relative h-workspace-body overflow-hidden bg-canvas">
      <div className="absolute left-4 top-4 z-sticky max-w-lg rounded-overlay border border-subtle bg-surface/90 px-3 py-2.5 shadow-raised backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1">
            <h1 className="text-heading text-primary">Bilgi grafı</h1>
            <p className="truncate text-meta text-muted">Notlar, görevler, kaynaklar ve aralarındaki bağlar</p>
          </div>
          <a href={backHref} className="inline-flex items-center gap-1.5 text-meta text-accent">
            <ArrowLeft size={13} /> {fromNotes ? "Notlara dön" : "Öğrenmeye dön"}
          </a>
          {focus && (
            <Button size="sm" onClick={() => navigate(fromNotes ? "/graph?from=notes" : "/graph")}>
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
            <span className="text-meta text-muted">Odaklı görünüm; bağlantı bu derinlikle paylaşılır.</span>
          </Toolbar>
        )}
      </div>
      <GraphView focus={focus} depth={depth} />
    </div>
  );
}
