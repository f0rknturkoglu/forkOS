import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";

import { api, qs } from "@/core/api";
import type { components } from "@/generated/api-schema";
import { Button, Chip, Empty, Section, relativeTime } from "@/core/ui";
import { actionLabel, measureLabel } from "./MediaProgressActions";

type MediaConsumption = components["schemas"]["MediaConsumptionOut"];
type ConsumptionPage = components["schemas"]["MediaConsumptionPageOut"];

const PAGE_SIZE = 20;

function ConsumptionRow({ row, unitTitle }: { row: MediaConsumption; unitTitle?: string }) {
  const amount = row.amount == null || row.amount === 0 ? null : `${row.amount} ${measureLabel(row.measure)}`;
  return (
    <li className="flex flex-wrap items-baseline gap-x-3 gap-y-1 py-2">
      <span className="w-24 shrink-0 text-meta text-muted">{relativeTime(row.occurred_at)}</span>
      <Chip size="xs">{actionLabel(row.action)}</Chip>
      {amount && <span className="text-body text-primary">{amount}</span>}
      {row.progress_after != null && (
        <span className="text-meta text-secondary">
          → {row.progress_after} {measureLabel(row.measure)}
        </span>
      )}
      {row.duration_min != null && <span className="text-meta text-muted">{row.duration_min} dk</span>}
      {unitTitle && <span className="text-meta text-secondary">{unitTitle}</span>}
      {row.note && <span className="basis-full text-meta text-muted">{row.note}</span>}
    </li>
  );
}

/**
 * Sayfali tuketim gecmisi (Faz 5): `GET /media/{id}/consumptions?limit=20`.
 *
 * Imlec sunucudan gelir (base64 offset) ve istemci onu yorumlamaz --
 * "Daha fazla yükle" yalnizca son sayfanin `next_cursor`'ini geri gonderir.
 * Yazma sonrasi ilk sayfa tazelenir; ek sayfalar sifirlanir ki liste
 * siralamasi tutarli kalsin.
 */
export function ConsumptionHistory({ itemId, unitTitles }: { itemId: string; unitTitles: Record<string, string> }) {
  const [extra, setExtra] = useState<ConsumptionPage[]>([]);
  const first = useQuery({
    queryKey: ["media", "consumptions", itemId],
    queryFn: () =>
      api.get<ConsumptionPage>(`/media/${encodeURIComponent(itemId)}/consumptions${qs({ limit: PAGE_SIZE })}`),
  });
  const more = useMutation({
    mutationFn: (cursor: string) =>
      api.get<ConsumptionPage>(`/media/${encodeURIComponent(itemId)}/consumptions${qs({ limit: PAGE_SIZE, cursor })}`),
    onSuccess: (page) => setExtra((current) => [...current, page]),
  });

  useEffect(() => {
    setExtra([]);
  }, [itemId, first.dataUpdatedAt]);

  const rows = [...(first.data?.items ?? []), ...extra.flatMap((page) => page.items)];
  const total = first.data?.total ?? rows.length;
  const nextCursor =
    extra.length > 0 ? (extra[extra.length - 1].next_cursor ?? null) : (first.data?.next_cursor ?? null);

  return (
    <Section title="Tüketim geçmişi" hint={first.data ? `${total} kayıt` : undefined}>
      {first.isLoading ? (
        <p role="status" className="text-body text-muted">
          Tüketim geçmişi yükleniyor…
        </p>
      ) : first.error ? (
        <p role="alert" className="text-meta text-danger">
          Tüketim geçmişi yüklenemedi: {first.error.message}
        </p>
      ) : rows.length === 0 ? (
        <Empty>Bu kayıt için henüz tüketim yok.</Empty>
      ) : (
        <ul className="divide-y divide-subtle">
          {rows.map((row) => (
            <ConsumptionRow
              key={row.id}
              row={row}
              unitTitle={row.unit_id ? unitTitles[String(row.unit_id)] : undefined}
            />
          ))}
        </ul>
      )}
      {nextCursor && (
        <div className="mt-3">
          <Button size="sm" disabled={more.isPending} onClick={() => more.mutate(nextCursor)}>
            <ChevronDown size={13} aria-hidden="true" /> {more.isPending ? "Yükleniyor…" : "Daha fazla yükle"}
          </Button>
        </div>
      )}
      {more.error && (
        <p role="alert" className="mt-2 text-meta text-danger">
          Tüketim geçmişi tamamlanamadı: {more.error.message}
        </p>
      )}
    </Section>
  );
}
