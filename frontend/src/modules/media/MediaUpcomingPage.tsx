import { useQuery } from "@tanstack/react-query";
import { CalendarClock } from "lucide-react";
import { api } from "@/core/api";
import type { components } from "@/generated/api-schema";
import { Button, Empty, PageFrame, PageHeader, RowList } from "@/core/ui";
import { Cover } from "./shared";

type MediaUnit = components["schemas"]["MediaUnitOut"];

function releaseLabel(unit: MediaUnit): string {
  if (!unit.release_at) return "Tarih yok";
  const date = new Date(unit.release_at);
  if (Number.isNaN(date.getTime())) return "Tarih yok";
  return date.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
}

export function MediaUpcomingPage() {
  const { data: units, isLoading, isFetching, isError, error, refetch } = useQuery({
    queryKey: ["media", "upcoming"],
    queryFn: () => api.get<MediaUnit[]>("/media/upcoming"),
  });

  return (
    <PageFrame className="space-y-6">
      <PageHeader eyebrow="Takip" title="Yaklaşan bölümler" />

      {isLoading ? (
        <p role="status" className="text-meta text-muted">Yaklaşan içerikler yükleniyor…</p>
      ) : isError ? (
        <Empty variant="page" action={<Button size="sm" disabled={isFetching} onClick={() => { void refetch(); }}>Yeniden dene</Button>}>
          Yaklaşan içerikler yüklenemedi: {error.message}
        </Empty>
      ) : !units || units.length === 0 ? (
        <Empty>Önümüzdeki 30 gün içinde yayınlanacak bölüm yok.</Empty>
      ) : (
        <RowList as="ul">
          {units.filter((unit) => !unit.parent_id).map((unit) => (
            <li key={unit.id} className="flex flex-wrap items-center gap-3 py-2.5">
              <Cover url={unit.cover_url ?? null} title={unit.title} size="h-16 w-11" />
              <div className="min-w-0 flex-1">
                <a
                  href={`#/media/${encodeURIComponent(unit.media_id)}`}
                  aria-label={`${unit.title} kaydını aç`}
                  className="block truncate text-body font-medium text-primary hover:text-accent hover:underline"
                >
                  {unit.number != null ? `${unit.number}. ` : ""}{unit.title}
                </a>
                <div className="mt-1 flex flex-wrap items-center gap-1.5 text-meta text-muted">
                  <CalendarClock size={13} aria-hidden="true" />
                  <span>{releaseLabel(unit)}</span>
                  {unit.duration_min != null && <span>· {unit.duration_min} dk</span>}
                </div>
              </div>
            </li>
          ))}
        </RowList>
      )}
    </PageFrame>
  );
}
