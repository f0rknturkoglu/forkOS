import { ExternalLink } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/core/api";
import { Button, Empty, Select, relativeTime } from "@/core/ui";
import { COLLECTIONS, COLLECTION_LABELS } from "@/core/types";
import type { Collection, FeedItem } from "@/core/types";

/** Tam metin ucu yaniti. Tip tanimlari modul icinde tutulur (core/types.ts'a dokunulmaz). */
interface FullTextResult {
  full_text: string | null;
}

/** href/src degerini denetler: yalnizca http/https/mailto semalari gecer. */
function safeUrl(raw: string): string {
  const value = raw.replace(/["'`]/g, "").replace(/&#x?[0-9a-f]+;/gi, "");
  const scheme = value.match(/^\s*([a-z][a-z0-9+.-]*)\s*:/i)?.[1] ?? "";
  return /^(?:http|https|mailto)$/i.test(scheme) ? value.trim() : "";
}

/** Feed HTML'ini okuma bölmesi için temizler. */
function sanitizeHtml(html: string): string {
  return html
    .replace(/<(script|style|iframe|object|embed|form|svg|math)\b[^>]*>[\s\S]*?<\/\1>/gi, "")
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/\s(href|src)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, (_, attr: string, raw: string) => {
      const value = safeUrl(raw);
      return value ? ` ${attr}="${value}"` : "";
    });
}

function stripHtml(html: string): string {
  return html
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function KbdInline({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="mx-1 rounded border border-strong bg-surface px-1 py-0.5 font-sans text-micro text-muted">
      {children}
    </kbd>
  );
}

interface RssReadingPaneProps {
  detail: FeedItem | undefined;
  online: boolean;
  saveCollection: Collection;
  onSaveCollection: (collection: Collection) => void;
  onToggleRead: () => void;
  onSave: () => void;
  onOpenBookmark: () => void;
  onPrev: () => void;
  onNext: () => void;
  hasPrev: boolean;
  hasNext: boolean;
}

export function RssReadingPane({
  detail,
  online,
  saveCollection,
  onSaveCollection,
  onToggleRead,
  onSave,
  onOpenBookmark,
  onPrev,
  onNext,
  hasPrev,
  hasNext,
}: RssReadingPaneProps) {
  // Tam metin durumu -- yazi degistiginde sifirlanir.
  const [view, setView] = useState<"summary" | "full">("summary");
  const [fullText, setFullText] = useState<string | null>(null);
  const [fetching, setFetching] = useState(false);
  const [notice, setNotice] = useState(false);
  const itemId = detail?.id ?? null;

  useEffect(() => {
    setView("summary");
    setFullText(null);
    setFetching(false);
    setNotice(false);
  }, [itemId]);

  if (!detail) {
    return (
      <Empty variant="page" title="Bir yazı seç">
        Soldaki listeden bir yazıya tıkla — içeriği burada okursun.
        <span className="mt-2 block text-meta text-muted">
          Kısayollar: <KbdInline>j</KbdInline> <KbdInline>k</KbdInline> gezin ·<KbdInline>u</KbdInline> okundu ·{" "}
          <KbdInline>s</KbdInline> kaydet · <KbdInline>⇧ J</KbdInline> sonraki okunmamış
        </span>
      </Empty>
    );
  }

  const hasBody = Boolean((detail.content || detail.summary || "").trim());
  const current = detail; // guard sonrasi daraltma closure'lara islemez

  /** Tam metni uctan ister: dolarsa tam metin moduna gecer, yoksa bilgi notu. */
  async function fetchFullText() {
    setFetching(true);
    setNotice(false);
    try {
      const result = await api.get<FullTextResult>(`/rss/items/${current.id}/fulltext`);
      if (result.full_text) {
        setFullText(result.full_text);
        setView("full");
      } else {
        setNotice(true);
      }
    } catch {
      setNotice(true);
    } finally {
      setFetching(false);
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 border-b border-subtle px-6 py-2.5">
        <Button size="sm" disabled={!online} onClick={onToggleRead}>
          {detail.read_at ? "Okunmadı" : "Okundu"}
        </Button>
        <Select
          disabled={!online || Boolean(detail.saved_bookmark_id)}
          value={saveCollection}
          onChange={(value) => onSaveCollection(value as Collection)}
          ariaLabel="Koleksiyon"
        >
          {COLLECTIONS.map((collection) => (
            <option key={collection} value={collection}>
              {COLLECTION_LABELS[collection]}
            </option>
          ))}
        </Select>
        {detail.saved_bookmark_id ? (
          <Button size="sm" variant="primary" onClick={onOpenBookmark} title="Yer iminde aç">
            Kaydedildi · aç →
          </Button>
        ) : (
          <Button size="sm" variant="primary" disabled={!online} onClick={onSave}>
            Yer imine kaydet
          </Button>
        )}
        {detail.url && (
          <Button
            size="sm"
            onClick={() => window.open(detail.url as string, "_blank", "noopener")}
            title="Orijinal sayfada aç"
          >
            <ExternalLink size={13} /> Orijinalini aç
          </Button>
        )}
        <span className="flex-1" />
        <Button size="sm" disabled={!hasPrev} onClick={onPrev} title="Önceki">
          ‹ Önceki
        </Button>
        <Button size="sm" disabled={!hasNext} onClick={onNext} title="Sonraki">
          Sonraki ›
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
        <h1 className="font-serif text-title leading-snug text-primary">{detail.title}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-meta text-muted">
          <span className="text-secondary">{detail.feed_title}</span>
          {detail.author && <span>· {detail.author}</span>}
          {detail.published_at && <span>· {relativeTime(detail.published_at)}</span>}
          {detail.url && (
            <a
              href={detail.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-accent hover:underline"
            >
              <ExternalLink size={12} /> orijinali
            </a>
          )}
        </div>

        {view === "full" && fullText ? (
          <div
            className="article-content mt-5 text-secondary"
            dangerouslySetInnerHTML={{ __html: sanitizeHtml(fullText) }}
          />
        ) : hasBody ? (
          detail.content ? (
            <div
              className="article-content mt-5 text-secondary"
              dangerouslySetInnerHTML={{ __html: sanitizeHtml(detail.content) }}
            />
          ) : (
            <p className="mt-5 whitespace-pre-wrap text-body leading-relaxed text-secondary">
              {stripHtml(detail.summary ?? "")}
            </p>
          )
        ) : (
          <p className="mt-5 text-body text-muted">
            Bu yazının özeti veya içeriği yok.{" "}
            {detail.url && (
              <a href={detail.url} target="_blank" rel="noreferrer" className="text-accent hover:underline">
                Orijinal sayfasında aç →
              </a>
            )}
          </p>
        )}

        {detail.url && view === "summary" && !fullText && (
          <div className="mt-4 flex items-center gap-3">
            <Button size="sm" disabled={!online || fetching} onClick={fetchFullText}>
              {fetching ? "Getiriliyor…" : "Tam metni getir"}
            </Button>
            {notice && <span className="text-meta text-muted">Tam metin alınamadı</span>}
          </div>
        )}

        {fullText && (
          <div className="mt-4 flex items-center gap-2">
            <Button size="sm" variant={view === "summary" ? "primary" : "ghost"} onClick={() => setView("summary")}>
              Özet
            </Button>
            <Button size="sm" variant={view === "full" ? "primary" : "ghost"} onClick={() => setView("full")}>
              Tam metin
            </Button>
          </div>
        )}
      </div>
    </>
  );
}
