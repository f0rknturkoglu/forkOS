import { invalidateAfter } from "./invalidation";
/**
 * İlgili kayıtlar paneli (Faz 3 — çekirdek bağ altyapısının ekran yüzü).
 *
 * Herhangi bir entity_id ile çalışır: ilişkili kayıtları ilişki etiketine göre
 * gruplar, satırlar kayıt defterindeki rotaya gider, "Bağla" global aramayla
 * POST /api/links yapar. Offline'da yazma kapalı (useOnline).
 */
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link2, Unlink, X } from "lucide-react";
import { api, qs } from "./api";
import { invalidate } from "./queryClient";
import { entityRoute, typeLabel } from "./entityRegistry";
import { Button, Chip, Empty, IconButton, Input, Section, cx, relativeTime } from "./ui";
import { useDebounced, useOnline } from "@/lib/hooks";
import type { Entity } from "./types";

interface RelatedRow {
  relation: string;
  direction: "outgoing" | "incoming";
  label: string;
  entity: { id: string; type: string; title: string; updated_at: string };
}

export function RelatedPanel({
  entityId,
  title = "İlgili kayıtlar",
  relation,
}: {
  entityId: string;
  title?: string;
  /** Yalniz bu iliskiyi gosterir ve yeni baglari bu iliskiyle kurar
   *  (ornek: learning'de konu -> kaynak "learns_from"). */
  relation?: string;
}) {
  const online = useOnline();
  const [picking, setPicking] = useState(false);
  const [query, setQuery] = useState("");
  const debounced = useDebounced(query.trim(), 250);

  const { data = [], refetch } = useQuery({
    queryKey: ["related", entityId],
    queryFn: () => api.get<RelatedRow[]>(`/entities/${entityId}/related`),
    select: (all) => (relation ? all.filter((row) => row.relation === relation) : all),
    enabled: Boolean(entityId),
  });
  // Savunma: gecersiz/eksik yanit paneli cokertmesin (Faz 18).
  const rows = Array.isArray(data) ? data : [];

  const { data: hits = {} } = useQuery({
    queryKey: ["search", debounced],
    queryFn: () => api.get<Record<string, Entity[]>>(`/search${qs({ q: debounced, limit: 8, grouped: true })}`),
    enabled: picking && debounced.length >= 2,
  });

  const link = useMutation({
    mutationFn: (toId: string) =>
      api.post("/links", { from_id: entityId, to_id: toId, relation: relation ?? "related" }),
    onSuccess: () => {
      setPicking(false);
      setQuery("");
      invalidateAfter("link.write");
    },
  });

  const unlink = useMutation({
    mutationFn: (row: RelatedRow) =>
      api.del("/links", { from_id: entityId, to_id: row.entity.id, relation: row.relation }),
    onSuccess: () => invalidateAfter("link.write"),
  });

  const grouped = rows.reduce<Record<string, RelatedRow[]>>((acc, row) => {
    (acc[row.label] ??= []).push(row);
    return acc;
  }, {});

  return (
    <Section
      title={title}
      action={
        <Button size="sm" disabled={!online} onClick={() => setPicking((v) => !v)}>
          <Link2 size={12} /> Bağla
        </Button>
      }
    >
      {picking && (
        <div className="mb-3 space-y-2">
          <div className="flex items-center gap-2">
            <Input value={query} onChange={setQuery} placeholder="Kayıt ara…" className="min-w-0 flex-1" />
            <IconButton
              title="Vazgeç"
              onClick={() => {
                setPicking(false);
                setQuery("");
              }}
            >
              <X size={14} />
            </IconButton>
          </div>
          {debounced.length >= 2 && (
            <div className="max-h-56 overflow-y-auto rounded-card border border-subtle">
              {Object.values(hits)
                .flat()
                .slice(0, 8)
                .map((hit) => (
                  <button
                    key={hit.id}
                    type="button"
                    disabled={hit.id === entityId || link.isPending}
                    onClick={() => link.mutate(hit.id)}
                    className="flex w-full items-center justify-between gap-2 border-b border-subtle px-3 py-2 text-left text-meta transition last:border-b-0 hover:bg-surface-hover disabled:opacity-40"
                  >
                    <span className="min-w-0 truncate">{hit.title}</span>
                    <Chip>{typeLabel(hit.type)}</Chip>
                  </button>
                ))}
            </div>
          )}
        </div>
      )}

      {rows.length === 0 ? (
        <Empty>Henüz bağlı kayıt yok.</Empty>
      ) : (
        Object.entries(grouped).map(([label, items]) => (
          <div key={label} className="mb-2 last:mb-0">
            <p className="label-caps mb-1 text-muted">{label}</p>
            <div className="divide-y divide-subtle rounded-card border border-subtle">
              {items.map((row) => (
                <div key={row.entity.id + row.relation} className="group flex items-center gap-2 px-3 py-2">
                  <a
                    href={`#${entityRoute(row.entity.type, row.entity.id).replace(/^#/, "")}`}
                    className="min-w-0 flex-1"
                  >
                    <span className="block truncate text-body text-primary hover:text-accent">{row.entity.title}</span>
                    <span className="text-meta text-muted">
                      {typeLabel(row.entity.type)} · {relativeTime(row.entity.updated_at)}
                    </span>
                  </a>
                  <IconButton
                    title="Bağı kaldır"
                    tone="danger"
                    disabled={!online || unlink.isPending}
                    className="opacity-0 transition group-hover:opacity-100"
                    onClick={() => unlink.mutate(row)}
                  >
                    <Unlink size={13} />
                  </IconButton>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </Section>
  );
}
