import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Highlighter, Quote } from "lucide-react";
import { api } from "@/core/api";
import type { Bookmark, GlobalHighlight } from "@/core/types";
import { Button, Empty, IconButton } from "@/core/ui";

type HighlightSource = GlobalHighlight | Bookmark;

export function highlightMarkdown(highlight: HighlightSource): string {
  const text = "text" in highlight ? highlight.text : highlight.selection ?? "";
  const title = "bookmark_title" in highlight ? highlight.bookmark_title : highlight.title;
  const url = "bookmark_url" in highlight ? highlight.bookmark_url : highlight.url;
  const quote = text.trim().replace(/\n/g, "\n> ");
  return `> ==${quote}==\n>\n> — [${title}](${url})`;
}

export function BookmarkHighlights({
  onInsert,
  onClose,
}: {
  onInsert: (markdown: string) => void;
  onClose: () => void;
}) {
  const { data: highlights = [], isLoading } = useQuery({
    queryKey: ["highlights"],
    queryFn: () => api.get<GlobalHighlight[]>("/highlights"),
  });

  return (
    <aside
      aria-label="Yer imi vurguları"
      className="fixed inset-y-0 right-0 z-drawer flex w-workspace-inspector flex-col border-l border-subtle bg-surface shadow-overlay"
    >
      <header className="flex items-center gap-2 border-b border-subtle px-3 py-3">
        <Highlighter size={15} className="text-icon" />
        <span className="min-w-0 flex-1 text-body font-medium text-primary">Vurgular</span>
        <Button size="sm" variant="ghost" onClick={onClose}>
          Kapat
        </Button>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {isLoading ? (
          <p className="text-meta text-muted">Vurgular yükleniyor…</p>
        ) : highlights.length === 0 ? (
          <Empty title="Henüz vurgu yok">Bir sayfadan metin seçip yer imlerine kaydettiğinde burada görünür.</Empty>
        ) : (
          <div className="space-y-2">
            {highlights.map((highlight) => (
              <article key={highlight.id} className="rounded-card border border-subtle bg-surface-sunken p-3">
                <div className="mb-2 flex items-start gap-2">
                  <Quote size={13} className="mt-0.5 shrink-0 text-icon" />
                  <p className="line-clamp-5 min-w-0 flex-1 text-meta leading-relaxed text-primary">
                    {highlight.text}
                  </p>
                </div>
                {highlight.note && <p className="mb-2 rounded-control bg-surface px-2 py-1.5 text-meta text-secondary">{highlight.note}</p>}
                <div className="flex items-center gap-2 border-t border-subtle pt-2">
                  <span className="min-w-0 flex-1 truncate text-micro text-muted">{highlight.bookmark_title}</span>
                  <a
                    href={highlight.bookmark_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    title="Kaynağı aç"
                    className="text-icon hover:text-primary"
                  >
                    <ExternalLink size={13} />
                  </a>
                  <IconButton title="Vurguyu nota ekle" onClick={() => onInsert(highlightMarkdown(highlight))}>
                    <Highlighter size={13} />
                  </IconButton>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
