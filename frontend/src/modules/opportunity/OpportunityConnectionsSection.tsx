import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Users } from "lucide-react";
import { api } from "@/core/api";
import { Chip, SectionHeader } from "@/core/ui";
import type { OpportunityConnections } from "@/core/types";

export function OpportunityConnectionsSection({ id }: { id: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["opportunity-connections", id],
    queryFn: () => api.get<OpportunityConnections>(`/opportunities/${id}/connections`),
  });

  if (isLoading) return <div className="h-20 animate-pulse rounded-card bg-surface-sunken" />;
  if (!data?.organization) return null;

  return (
    <section className="rounded-card border border-subtle bg-surface p-4 shadow-card">
      <SectionHeader
        label="Warm intro"
        hint={
          data.connections.length > 0
            ? `${data.organization} kurumunda ${data.connections.length} bağlantı`
            : `${data.organization} için bağlantı bulunamadı`
        }
        action={<Users size={15} className={data.connections.length ? "text-accent" : "text-muted"} />}
      />
      {data.connections.length === 0 ? (
        <p className="mt-3 text-meta text-muted">Yerel LinkedIn bağlantı ağında bu kurumla eşleşen kişi yok.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {data.connections.map((connection) => (
            <li
              key={connection.id}
              className="flex items-center gap-3 rounded-control border border-subtle bg-surface-sunken px-3 py-2"
            >
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface text-muted">
                <Users size={13} />
              </span>
              <div className="min-w-0 flex-1">
                <strong className="block truncate text-body text-primary">{connection.name}</strong>
                <span className="block truncate text-meta text-secondary">
                  {[connection.position, connection.company].filter(Boolean).join(" · ") || "Bağlam belirtilmemiş"}
                </span>
              </div>
              {connection.connected_on && (
                <Chip>{new Date(`${connection.connected_on}T00:00:00`).toLocaleDateString("tr-TR")}</Chip>
              )}
              {connection.profile_url && (
                <a
                  href={connection.profile_url}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={`${connection.name} profilini aç`}
                  title={`${connection.name} profilini aç`}
                  className="text-muted transition hover:text-primary"
                >
                  <ExternalLink size={14} />
                </a>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
