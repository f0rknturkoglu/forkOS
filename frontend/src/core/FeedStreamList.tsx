import { BookOpen, Flame, Github, MessageSquare, Rss, Star, TrendingUp } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { navigate } from "@/app/router";
import { Button, RowList, cx, relativeTime } from "@/core/ui";
import type { FeedOrigin, StreamItem } from "./feedStream";

/**
 * Okuma akışı satırları — Home widget'ı ve Okuma Akışı sayfası AYNI bileşeni
 * kullanır. Kaynak kimliği (ikon + renk), dış bağlantı davranışı ve RSS
 * satırının yerel okuyucuya gitmesi tek yerde tanımlıdır.
 */

/** Kaynak kimliği: ikon + renk. Renkler markadan gelir (semantik değil),
 *  index.css'te --feed-* olarak tanımlı. */
const ORIGIN: Record<FeedOrigin, { icon: LucideIcon; text: string }> = {
  hf: { icon: BookOpen, text: "text-accent" },
  rss: { icon: Rss, text: "text-feed-rss" },
  reddit: { icon: MessageSquare, text: "text-feed-reddit" },
  hn: { icon: Flame, text: "text-feed-hn" },
  gh: { icon: Github, text: "text-feed-gh" },
};

export function FeedSourceFailures({
  failures,
}: {
  failures: { origin: FeedOrigin; label: string; retry: () => void }[];
}) {
  if (failures.length === 0) return null;
  return (
    <div className="mb-1 flex flex-wrap items-center gap-2 border-b border-warn-border px-2 py-2 text-meta text-warn">
      {failures.map((source) => (
        <span key={source.origin} className="inline-flex items-center gap-1.5">
          {source.label} alınamadı.
          <Button
            size="sm"
            variant="ghost"
            ariaLabel={`${source.label}'i yeniden dene`}
            onClick={source.retry}
            className="h-auto px-1.5 py-0.5 text-warn"
          >
            yeniden dene
          </Button>
        </span>
      ))}
    </div>
  );
}

export function FeedStreamList({ items, empty }: { items: StreamItem[]; empty?: string }) {
  if (items.length === 0) {
    return <p className="px-2 py-4 text-center text-meta text-muted">{empty ?? "Yeni bir şey yok."}</p>;
  }
  return (
    <RowList>
      {items.map((item) => {
        const skin = ORIGIN[item.origin];
        const Icon = skin.icon;
        return (
          <div key={item.key} className="flex items-start gap-2.5 py-2">
            <Icon size={13} className={cx("mt-1 shrink-0", skin.text)} />
            <div className="min-w-0 flex-1">
              {item.href ? (
                <a
                  href={item.href}
                  target="_blank"
                  rel="noreferrer"
                  className="line-clamp-2 text-body font-medium text-primary hover:text-accent"
                >
                  {item.title}
                </a>
              ) : (
                <button
                  type="button"
                  onClick={() => navigate("/rss")}
                  className={cx(
                    "block w-full truncate text-left text-body hover:text-accent",
                    item.unread ? "font-medium text-primary" : "text-secondary",
                  )}
                >
                  {item.title}
                </button>
              )}
              {item.subtitle && <p className="mt-0.5 line-clamp-1 text-meta text-secondary">{item.subtitle}</p>}
              <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-meta text-muted">
                <span
                  className={cx(
                    "rounded border border-subtle px-1.5 py-0.5 text-micro leading-4",
                    item.origin === "gh" ? technologyChip(item.source) : skin.text,
                  )}
                >
                  {item.source}
                </span>
                {item.host && <span className="max-w-[40%] truncate">{item.host}</span>}
                {item.score !== null && (
                  <span className="flex items-center gap-1">
                    {item.scoreIcon === "stars" ? <Star size={11} /> : <TrendingUp size={11} />}
                    {item.score}
                  </span>
                )}
                {item.commentsUrl && (
                  <a href={item.commentsUrl} target="_blank" rel="noreferrer" className="hover:text-primary">
                    yorumlar
                  </a>
                )}
                {item.at > 0 && <span>{relativeTime(new Date(item.at).toISOString())}</span>}
              </p>
            </div>
          </div>
        );
      })}
    </RowList>
  );
}

export function technologyChip(language: string): string {
  const key = language
    .toLowerCase()
    .replace(/\+/g, "p")
    .replace(/#/g, "sharp")
    .replace(/[^a-z0-9]/g, "");
  const palette: Record<string, string> = {
    typescript: "typescript",
    javascript: "javascript",
    python: "python",
    swift: "swift",
    rust: "rust",
    go: "go",
    java: "java",
    kotlin: "kotlin",
    c: "c",
    cpp: "cpp",
    csharp: "csharp",
    ruby: "ruby",
    php: "php",
    dart: "dart",
    html: "html",
    css: "css",
    shell: "shell",
  };
  return palette[key] ? `technology-chip technology-chip-${palette[key]}` : "text-feed-gh";
}
