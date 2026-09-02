/**
 * Backlink paneli: bu kayda [[...]] ile baglanan notlar/kayitlar.
 *
 * Kaynak `link` tablosundaki `mentions` iliskisidir -- yani baglar not
 * govdesinden turuyor, elle kurulmuyor. Elle kurulan iliskiler icin
 * RelatedPanel var; ikisi ayri seyler ve ayri panellerde gosterilir.
 */
import { useQuery } from "@tanstack/react-query";
import { CornerDownLeft } from "lucide-react";
import { api } from "./api";
import { entityRoute, typeLabel } from "./entityRegistry";
import { Chip, Empty, RowList, Section } from "./ui";

interface BacklinkRow {
  id: string;
  type: string;
  title: string;
}

export function BacklinksPanel({ entityId, title = "Buraya bağlananlar" }: { entityId: string; title?: string }) {
  const { data = [], isLoading } = useQuery({
    queryKey: ["backlinks", entityId],
    enabled: Boolean(entityId),
    queryFn: () => api.get<BacklinkRow[]>(`/entities/${entityId}/backlinks`),
  });

  return (
    <Section title={title} hint={data.length ? `${data.length} bağlantı` : undefined}>
      {isLoading ? (
        <Empty>Yükleniyor…</Empty>
      ) : data.length === 0 ? (
        <Empty>Henüz kimse buraya bağlanmamış. Bir notta [[{"başlık"}]] yazınca burada görünür.</Empty>
      ) : (
        <RowList>
          {data.map((row) => (
            <a
              key={row.id}
              href={`#${entityRoute(row.type, row.id)}`}
              className="flex items-center gap-2.5 py-2 text-body text-primary transition hover:text-accent"
            >
              <CornerDownLeft size={14} className="shrink-0 text-muted" />
              <span className="min-w-0 flex-1 truncate">{row.title}</span>
              <Chip size="xs">{typeLabel(row.type)}</Chip>
            </a>
          ))}
        </RowList>
      )}
    </Section>
  );
}
