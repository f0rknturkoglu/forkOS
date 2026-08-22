import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { api } from "@/core/api";
import { Section } from "@/core/ui";
import type { AppSettings } from "@/core/types";

/** Hizli linkler (media.links). Arama kutusu ust seritte -- burada tekrar etmez. */
export function QuickLinksWidget() {
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<AppSettings>("/settings"),
  });
  const links = (settings?.["media.links"] ?? []) as { name: string; url: string }[];

  return (
    <Section title="Hızlı erişim">
      {links.length === 0 ? (
        <p className="text-meta text-muted">
          Ayarlar'dan hızlı link ekle (Letterboxd, Goodreads…).
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-1.5">
          {links.map((link) => (
            <a
              key={link.name}
              href={link.url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 rounded-control border border-subtle px-2.5 py-1.5 text-meta text-secondary transition hover:border-strong hover:text-primary"
            >
              <ExternalLink size={12} className="shrink-0 text-icon" />
              <span className="truncate">{link.name}</span>
            </a>
          ))}
        </div>
      )}
    </Section>
  );
}
