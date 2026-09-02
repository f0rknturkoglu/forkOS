/**
 * Bilgi grafi sayfasi -- second brain'in haritasi.
 *
 * Odak (?focus={id}) verilirse o kaydin cevresi, verilmezse tum graf.
 * Derinlik URL'de yasar ki paylasilan baglanti ayni gorunumu acsin.
 */
import { useHashRoute, navigate } from "@/app/router";
import { GraphView } from "@/core/GraphView";
import { Button, PageFrame, PageHeader, Toolbar } from "@/core/ui";

const DEPTHS = [1, 2, 3];

export function GraphPage() {
  const route = useHashRoute();
  const focus = route.params.get("focus") ?? undefined;
  const depth = Number(route.params.get("depth") ?? 2);

  const go = (next: number) =>
    navigate(`/graph?${new URLSearchParams({ ...(focus ? { focus } : {}), depth: String(next) })}`);

  return (
    <PageFrame className="space-y-5">
      <PageHeader
        eyebrow="Öğrenme"
        title="Bilgi grafı"
        action={
          focus ? (
            <Button size="sm" onClick={() => navigate("/graph")}>
              Tüm grafı gör
            </Button>
          ) : undefined
        }
      />
      <p className="text-meta text-muted">
        Düğümler kayıtlar, bağlar notlardaki [[wikilink]]’ler ve elle kurulan ilişkiler. Bir düğüme tıkla, kaydına git.
      </p>
      {focus && (
        <Toolbar>
          <span className="text-meta text-muted">Komşuluk derinliği:</span>
          {DEPTHS.map((value) => (
            <Button key={value} size="sm" variant={depth === value ? "primary" : "ghost"} onClick={() => go(value)}>
              {value}
            </Button>
          ))}
        </Toolbar>
      )}
      <GraphView focus={focus} depth={depth} />
    </PageFrame>
  );
}
