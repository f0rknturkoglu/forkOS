import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  Check,
  CheckSquare,
  Clock,
  Columns,
  ExternalLink,
  Highlighter,
  Layers,
  RefreshCw,
  Star,
  Trash2,
  X,
} from "lucide-react";
import { api, qs } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import type { Bookmark, BookmarkFullText, BookmarkHighlight, Collection } from "@/core/types";
import {
  Button,
  Chip,
  Empty,
  IconButton,
  Input,
  Select,
  cx,
  hostOf,
  useToast,
} from "@/core/ui";

export interface BookmarkReaderModalProps {
  open: boolean;
  bookmark: Bookmark | null;
  onClose: () => void;
  onBookmarkUpdated?: (updated: Bookmark) => void;
}

type FontFamilyChoice = "serif" | "sans";
type FontSizeChoice = "sm" | "md" | "lg";
type ColumnWidthChoice = "normal" | "wide";
type HighlightColor = "yellow" | "green" | "blue" | "pink";

function safeUrl(raw: string): string {
  const value = raw.replace(/["'`]/g, "").replace(/&#x?[0-9a-f]+;/gi, "");
  const scheme = value.match(/^\s*([a-z][a-z0-9+.-]*)\s*:/i)?.[1] ?? "";
  return /^(?:http|https|mailto)$/i.test(scheme) ? value.trim() : "";
}

function sanitizeHtml(html: string): string {
  return html
    .replace(/<(script|style|iframe|object|embed|form|svg|math)\b[^>]*>[\s\S]*?<\/\1>/gi, "")
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/\s(href|src)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, (_, attr: string, raw: string) => {
      const value = safeUrl(raw);
      return value ? ` ${attr}="${value}"` : "";
    });
}

const COLOR_STYLES: Record<HighlightColor, { badge: string; chip: string }> = {
  yellow: {
    badge: "bg-warn-surface text-warn border-warn-border",
    chip: "bg-warn-surface border-warn-border",
  },
  green: {
    badge: "bg-ok-surface text-ok border-ok-border",
    chip: "bg-ok-surface border-ok-border",
  },
  blue: {
    badge: "bg-accent-surface text-accent border-accent-border",
    chip: "bg-accent-surface border-accent-border",
  },
  pink: {
    badge: "bg-danger-surface text-danger border-danger-border",
    chip: "bg-danger-surface border-danger-border",
  },
};

function safeGetStorage(key: string, fallback: string): string {
  try {
    if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
      return localStorage.getItem(key) || fallback;
    }
  } catch {
    // ignore
  }
  return fallback;
}

function safeSetStorage(key: string, value: string): void {
  try {
    if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
      localStorage.setItem(key, value);
    }
  } catch {
    // ignore
  }
}

export function BookmarkReaderModal({
  open,
  bookmark,
  onClose,
  onBookmarkUpdated,
}: BookmarkReaderModalProps) {
  const toast = useToast();
  const scrollRef = useRef<HTMLDivElement>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [fontFamily, setFontFamily] = useState<FontFamilyChoice>(() => {
    return (safeGetStorage("forkos_reader_font", "serif") as FontFamilyChoice);
  });
  const [fontSize, setFontSize] = useState<FontSizeChoice>(() => {
    return (safeGetStorage("forkos_reader_size", "md") as FontSizeChoice);
  });
  const [columnWidth, setColumnWidth] = useState<ColumnWidthChoice>(() => {
    return (safeGetStorage("forkos_reader_width", "normal") as ColumnWidthChoice);
  });

  const [showHighlightsPanel, setShowHighlightsPanel] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(bookmark?.scroll_progress ?? 0);
  const [selectionPopup, setSelectionPopup] = useState<{
    text: string;
    top: number;
    left: number;
  } | null>(null);
  const [selectedColor, setSelectedColor] = useState<HighlightColor>("yellow");
  const [highlightNote, setHighlightNote] = useState("");

  const [localReadStatus, setLocalReadStatus] = useState<string>(bookmark?.read_status ?? "unread");
  const [localFavorite, setLocalFavorite] = useState<boolean>(bookmark?.is_favorite ?? false);
  const [localCollection, setLocalCollection] = useState<Collection>(
    bookmark?.collection ?? "read_later",
  );

  useEffect(() => {
    if (bookmark) {
      setScrollProgress(bookmark.scroll_progress ?? 0);
      setLocalReadStatus(bookmark.read_status ?? "unread");
      setLocalFavorite(bookmark.is_favorite ?? false);
      setLocalCollection(bookmark.collection ?? "read_later");
      setSelectionPopup(null);
      setHighlightNote("");
    }
  }, [bookmark?.id]);

  useEffect(() => {
    safeSetStorage("forkos_reader_font", fontFamily);
  }, [fontFamily]);

  useEffect(() => {
    safeSetStorage("forkos_reader_size", fontSize);
  }, [fontSize]);

  useEffect(() => {
    safeSetStorage("forkos_reader_width", columnWidth);
  }, [columnWidth]);

  // ESC ile kapatma
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (selectionPopup) {
          setSelectionPopup(null);
        } else {
          onClose();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, selectionPopup, onClose]);

  // Tam metin ve vurgulari getir
  const {
    data: fullText,
    isLoading,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ["bookmarks", bookmark?.id, "fulltext"],
    queryFn: () => api.get<BookmarkFullText>(`/bookmarks/${bookmark?.id}/fulltext`),
    enabled: open && Boolean(bookmark?.id),
  });

  // Ilerleme kaydetme (debounce)
  const saveProgress = (pct: number) => {
    if (!bookmark) return;
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(async () => {
      try {
        const res = await api.patch<{ scroll_progress: number; read_status: string }>(
          `/bookmarks/${bookmark.id}/progress`,
          { scroll_progress: pct },
        );
        if (res.read_status === "read" && localReadStatus !== "read") {
          setLocalReadStatus("read");
          toast.push("Makale okundu olarak isaretlendi", { tone: "ok" });
          invalidateAfter("bookmark.write");
        }
      } catch {
        // Sessiz hata
      }
    }, 400);
  };

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const total = el.scrollHeight - el.clientHeight;
    if (total <= 0) return;
    const pct = Math.min(100, Math.max(0, Math.round((el.scrollTop / total) * 100)));
    setScrollProgress(pct);
    saveProgress(pct);
  };

  // Metin secim araci (Floating Toolbar)
  const handleTextSelection = (e: React.MouseEvent) => {
    // Toolbar uzerine tiklandiysa secimi koru
    if ((e.target as HTMLElement).closest("[data-highlight-toolbar]")) {
      return;
    }

    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) {
      setSelectionPopup(null);
      return;
    }

    const text = sel.toString().trim();
    if (text.length < 2) {
      setSelectionPopup(null);
      return;
    }

    try {
      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      setSelectionPopup({
        text,
        top: Math.max(12, rect.top - 70),
        left: Math.max(12, rect.left + rect.width / 2 - 140),
      });
    } catch {
      setSelectionPopup(null);
    }
  };

  // Vurgu Ekle
  const addHighlight = useMutation({
    mutationFn: (data: { text: string; note?: string; color: HighlightColor }) =>
      api.post<BookmarkHighlight>(`/bookmarks/${bookmark?.id}/highlights`, {
        ...data,
        anchor_index: 0,
      }),
    onSuccess: () => {
      invalidateAfter("bookmark.write");
      toast.push("Vurgu kaydedildi", { tone: "ok" });
      setSelectionPopup(null);
      setHighlightNote("");
      refetch();
    },
  });

  // Vurgu Sil
  const deleteHighlight = useMutation({
    mutationFn: (highlightId: string) =>
      api.del(`/bookmarks/${bookmark?.id}/highlights/${highlightId}`),
    onSuccess: () => {
      invalidateAfter("bookmark.write");
      toast.push("Vurgu silindi", { tone: "neutral" });
      refetch();
    },
  });

  // Vurguyu Flashcard'a Donustur
  const convertHighlightToFlashcard = useMutation({
    mutationFn: (highlightId: string) =>
      api.post<{ card_id: string }>(
        `/bookmarks/${bookmark?.id}/highlights/${highlightId}/convert-to-flashcard`,
        {},
      ),
    onSuccess: () => {
      invalidateAfter("flashcard.write", "link.write");
      toast.push("Flashcard karti olusturuldu", { tone: "ok" });
    },
  });

  // Secilen metni dogrudan Flashcard yap
  const handleConvertSelectionToFlashcard = async () => {
    if (!bookmark || !selectionPopup) return;
    try {
      const hl = await addHighlight.mutateAsync({
        text: selectionPopup.text,
        note: highlightNote || undefined,
        color: selectedColor,
      });
      if (hl?.id) {
        await convertHighlightToFlashcard.mutateAsync(hl.id);
      }
    } catch {
      toast.push("Flashcard olusturulamadi", { tone: "danger" });
    }
  };

  // Secilen metni Gorev yap
  const handleConvertSelectionToTodo = async () => {
    if (!bookmark || !selectionPopup) return;
    try {
      await api.post("/todos", {
        title: `Okuma: ${selectionPopup.text.slice(0, 80)}`,
        notes: `${selectionPopup.text}${highlightNote ? `\n\nNot: ${highlightNote}` : ""}\n\nKaynak: ${bookmark.url}`,
        priority: 2,
      });
      invalidateAfter("todo.write");
      toast.push("Gorev olusturuldu", { tone: "ok" });
      setSelectionPopup(null);
      setHighlightNote("");
    } catch {
      toast.push("Gorev olusturulamadi", { tone: "danger" });
    }
  };

  // Okundu / Okunmadi degisimi
  const toggleReadStatus = useMutation({
    mutationFn: () => {
      const nextStatus = localReadStatus === "read" ? "unread" : "read";
      return api.patch<Bookmark>(`/bookmarks/${bookmark?.id}`, { read_status: nextStatus });
    },
    onSuccess: (updated) => {
      setLocalReadStatus(updated.read_status);
      invalidateAfter("bookmark.write");
      onBookmarkUpdated?.(updated);
      toast.push(
        updated.read_status === "read" ? "Okundu olarak isaretlendi" : "Okunmadi olarak isaretlendi",
        { tone: "ok" },
      );
    },
  });

  // Favori degisimi
  const toggleFavorite = useMutation({
    mutationFn: () =>
      api.patch<Bookmark>(`/bookmarks/${bookmark?.id}`, { is_favorite: !localFavorite }),
    onSuccess: (updated) => {
      setLocalFavorite(updated.is_favorite);
      invalidateAfter("bookmark.write");
      onBookmarkUpdated?.(updated);
      toast.push(
        updated.is_favorite ? "Favorilere eklendi" : "Favorilerden cikarildi",
        { tone: "neutral" },
      );
    },
  });

  // Koleksiyon degisimi
  const updateCollection = useMutation({
    mutationFn: (collection: Collection) =>
      api.patch<Bookmark>(`/bookmarks/${bookmark?.id}/collection${qs({ collection })}`),
    onSuccess: (updated) => {
      setLocalCollection(updated.collection);
      invalidateAfter("bookmark.write");
      onBookmarkUpdated?.(updated);
      toast.push(`Koleksiyon guncellendi: ${updated.collection}`, { tone: "ok" });
    },
  });

  if (!open || !bookmark) return null;

  const isRead = localReadStatus === "read";
  const highlights = fullText?.highlights ?? [];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={bookmark.title || "Okuma Modu"}
      className="fixed inset-0 z-modal flex items-center justify-center bg-[color:var(--overlay-scrim)] p-2 sm:p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative flex h-[95vh] w-full max-w-5xl flex-col rounded-overlay border border-strong bg-surface shadow-overlay outline-none overflow-hidden">
        {/* Ust Kaydirma Ilerleme Cubugu */}
        <div className="h-1 w-full bg-surface-sunken shrink-0">
          <div
            className="h-full bg-accent transition-all duration-150"
            style={{ width: `${scrollProgress}%` }}
          />
        </div>

        {/* Ust Arac Cubugu */}
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-subtle bg-surface px-4 py-2.5 shrink-0">
          {/* Sol Kisim: Kapat, Alan Adi, Koleksiyon */}
          <div className="flex items-center gap-2 min-w-0">
            <IconButton title="Kapat (Esc)" onClick={onClose}>
              <X size={16} />
            </IconButton>
            <span className="truncate text-meta font-medium text-primary max-w-xs font-mono">
              {hostOf(bookmark.url)}
            </span>
            <Select
              value={localCollection}
              onChange={(c) => updateCollection.mutate(c as Collection)}
              className="text-meta"
            >
              <option value="read_later">Daha Sonra Oku</option>
              <option value="inbox">Gelen Kutusu</option>
              <option value="archive">Arsiv</option>
              <option value="learning">Ogrenme</option>
              <option value="projects">Projeler</option>
            </Select>
          </div>

          {/* Sag Kisim: Okuma Kontrolleri */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {/* Serif / Sans Font Gecisi */}
            <div className="flex items-center rounded-control border border-subtle bg-surface-sunken p-0.5">
              <button
                type="button"
                onClick={() => setFontFamily("serif")}
                className={cx(
                  "px-2 py-1 text-meta rounded-control transition-colors font-serif",
                  fontFamily === "serif"
                    ? "bg-surface text-primary shadow-xs font-medium"
                    : "text-muted hover:text-primary",
                )}
              >
                Serif
              </button>
              <button
                type="button"
                onClick={() => setFontFamily("sans")}
                className={cx(
                  "px-2 py-1 text-meta rounded-control transition-colors font-sans",
                  fontFamily === "sans"
                    ? "bg-surface text-primary shadow-xs font-medium"
                    : "text-muted hover:text-primary",
                )}
              >
                Sans
              </button>
            </div>

            {/* Punto Degisimi */}
            <div className="flex items-center rounded-control border border-subtle bg-surface-sunken p-0.5">
              {(["sm", "md", "lg"] as const).map((size) => (
                <button
                  key={size}
                  type="button"
                  onClick={() => setFontSize(size)}
                  className={cx(
                    "px-2 py-1 text-meta rounded-control transition-colors",
                    fontSize === size
                      ? "bg-surface text-primary shadow-xs font-medium"
                      : "text-muted hover:text-primary",
                  )}
                >
                  {size === "sm" ? "A-" : size === "md" ? "A" : "A+"}
                </button>
              ))}
            </div>

            {/* Sutun Genisligi */}
            <IconButton
              title={columnWidth === "normal" ? "Genis sutun" : "Dar sutun"}
              onClick={() => setColumnWidth(columnWidth === "normal" ? "wide" : "normal")}
            >
              <Columns size={15} />
            </IconButton>

            {/* Vurgular Paneli Ac/Kapa */}
            <Button
              size="sm"
              variant={showHighlightsPanel ? "primary" : "secondary"}
              onClick={() => setShowHighlightsPanel(!showHighlightsPanel)}
            >
              <Highlighter size={13} />
              <span>{highlights.length > 0 ? `Vurgular (${highlights.length})` : "Vurgular"}</span>
            </Button>

            {/* Okundu / Okunmadi */}
            <Button
              size="sm"
              variant={isRead ? "secondary" : "primary"}
              onClick={() => toggleReadStatus.mutate()}
            >
              {isRead ? <Check size={14} /> : <BookOpen size={14} />}
              <span>{isRead ? "Okundu" : "Okunmadi"}</span>
            </Button>

            {/* Favori */}
            <IconButton
              title={localFavorite ? "Favorilerden cikar" : "Favoriye ekle"}
              onClick={() => toggleFavorite.mutate()}
            >
              <Star size={15} className={cx(localFavorite && "fill-accent text-accent")} />
            </IconButton>

            {/* Orijinal Sayfa Baglantisi */}
            <a
              href={bookmark.url}
              target="_blank"
              rel="noreferrer"
              title="Orijinal sayfayi ac"
              className="inline-flex items-center justify-center p-1.5 rounded-control text-muted hover:text-primary hover:bg-surface-hover"
            >
              <ExternalLink size={15} />
            </a>
          </div>
        </header>

        {/* Ana Govde */}
        <div className="flex min-h-0 flex-1 overflow-hidden">
          {/* Makale Okuma Alani */}
          <div
            ref={scrollRef}
            onScroll={handleScroll}
            onMouseUp={handleTextSelection}
            className="relative flex-1 overflow-y-auto px-6 py-8 select-text"
          >
            <article
              className={cx(
                "mx-auto transition-all duration-150",
                columnWidth === "normal" ? "max-w-2xl" : "max-w-4xl",
                fontFamily === "serif" ? "font-serif" : "font-sans",
                fontSize === "sm" ? "text-meta" : fontSize === "md" ? "text-body" : "text-heading",
              )}
            >
              {/* Makale Ust Bilgileri */}
              <div className="mb-8 border-b border-subtle pb-6 font-sans">
                <div className="flex flex-wrap items-center gap-2 text-meta text-muted mb-3">
                  <span className="font-mono">{hostOf(bookmark.url)}</span>
                  {fullText?.author && (
                    <>
                      <span>·</span>
                      <span>{fullText.author}</span>
                    </>
                  )}
                  {fullText?.reading_time_min ? (
                    <>
                      <span>·</span>
                      <Chip tone="accent">
                        <Clock size={11} className="mr-1 inline" />
                        {fullText.reading_time_min} dk okuma
                      </Chip>
                    </>
                  ) : null}
                  {fullText?.word_count ? (
                    <>
                      <span>·</span>
                      <span>{fullText.word_count.toLocaleString("tr-TR")} kelime</span>
                    </>
                  ) : null}
                  {scrollProgress > 0 && (
                    <>
                      <span>·</span>
                      <span className="text-accent font-medium">%{scrollProgress} okundu</span>
                    </>
                  )}
                </div>

                <h1 className="text-display font-semibold text-primary leading-tight break-words">
                  {bookmark.title || bookmark.url}
                </h1>

                {bookmark.note && (
                  <p className="mt-3 text-meta text-muted italic bg-surface-sunken p-3 rounded-control border border-subtle">
                    {bookmark.note}
                  </p>
                )}
              </div>

              {/* Hero Kapak Gorseli */}
              {(fullText?.hero_image_url || bookmark.hero_image_url) && (
                <div className="mb-8 overflow-hidden rounded-control border border-subtle">
                  <img
                    src={fullText?.hero_image_url || bookmark.hero_image_url || ""}
                    alt={bookmark.title}
                    className="w-full max-h-96 object-cover"
                  />
                </div>
              )}

              {/* Icerik */}
              {isLoading ? (
                <div className="space-y-4 py-8">
                  <div className="h-4 w-3/4 animate-pulse rounded-control bg-surface-sunken" />
                  <div className="h-4 w-full animate-pulse rounded-control bg-surface-sunken" />
                  <div className="h-4 w-5/6 animate-pulse rounded-control bg-surface-sunken" />
                  <div className="h-4 w-2/3 animate-pulse rounded-control bg-surface-sunken" />
                </div>
              ) : fullText?.content_html ? (
                <div
                  className="article-content leading-relaxed space-y-4 text-secondary"
                  dangerouslySetInnerHTML={{ __html: sanitizeHtml(fullText.content_html) }}
                />
              ) : (
                <div className="py-8 text-center space-y-4 font-sans">
                  <p className="text-body text-muted">
                    Bu yer iminin tam metni henuz cekilmedi veya sayfa icerigi temizlenemedi.
                  </p>
                  <div className="flex justify-center gap-3">
                    <Button
                      variant="primary"
                      onClick={() => refetch()}
                      disabled={isFetching}
                    >
                      <RefreshCw size={14} className={cx(isFetching && "animate-spin")} />
                      <span>Tam Metni Tekrar Getir</span>
                    </Button>
                    <a
                      href={bookmark.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 text-body text-accent hover:underline"
                    >
                      <span>Orijinal sayfayi ac</span>
                      <ExternalLink size={14} />
                    </a>
                  </div>
                </div>
              )}
            </article>
          </div>

          {/* Vurgular Yan Paneli */}
          {showHighlightsPanel && (
            <aside
              aria-label="Vurgular Paneli"
              className="w-80 border-l border-subtle bg-surface-sunken flex flex-col shrink-0"
            >
              <header className="flex items-center justify-between border-b border-subtle px-3 py-3">
                <div className="flex items-center gap-2">
                  <Highlighter size={14} className="text-icon" />
                  <span className="text-body font-medium text-primary">
                    Vurgular ({highlights.length})
                  </span>
                </div>
                <IconButton title="Paneli Kapat" onClick={() => setShowHighlightsPanel(false)}>
                  <X size={14} />
                </IconButton>
              </header>

              <div className="min-h-0 flex-1 overflow-y-auto p-3 space-y-3">
                {highlights.length === 0 ? (
                  <Empty title="Henuz vurgu yok">
                    Makale uzerinde metin secerek vurgu ve not ekleyebilirsiniz.
                  </Empty>
                ) : (
                  highlights.map((h) => {
                    const colorStyle = COLOR_STYLES[(h.color as HighlightColor) || "yellow"];
                    return (
                      <article
                        key={h.id}
                        className="rounded-card border border-subtle bg-surface p-3 space-y-2 shadow-xs"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span
                            className={cx(
                              "text-micro font-medium px-1.5 py-0.5 rounded-control border",
                              colorStyle.badge,
                            )}
                          >
                            {h.color}
                          </span>
                          <div className="flex items-center gap-1">
                            <IconButton
                              title="Flashcard yap"
                              onClick={() => convertHighlightToFlashcard.mutate(h.id)}
                            >
                              <Layers size={13} />
                            </IconButton>
                            <IconButton
                              title="Vurguyu sil"
                              onClick={() => deleteHighlight.mutate(h.id)}
                            >
                              <Trash2 size={13} />
                            </IconButton>
                          </div>
                        </div>

                        <p className="text-meta text-primary leading-relaxed font-serif italic border-l-2 border-subtle pl-2">
                          &ldquo;{h.text}&rdquo;
                        </p>

                        {h.note && (
                          <p className="text-meta text-muted bg-surface-sunken p-2 rounded-control">
                            {h.note}
                          </p>
                        )}
                      </article>
                    );
                  })
                )}
              </div>
            </aside>
          )}
        </div>

        {/* Metin Secim Araci (Floating Toolbar) */}
        {selectionPopup && (
          <div
            data-highlight-toolbar
            style={{ top: selectionPopup.top, left: selectionPopup.left }}
            className="fixed z-popover flex flex-col gap-2 rounded-control border border-strong bg-surface p-2 shadow-overlay font-sans"
          >
            <div className="flex items-center gap-1.5">
              {(["yellow", "green", "blue", "pink"] as const).map((color) => (
                <button
                  key={color}
                  type="button"
                  title={`${color} vurgula`}
                  onClick={() => setSelectedColor(color)}
                  className={cx(
                    "w-5 h-5 rounded-full border transition-transform",
                    COLOR_STYLES[color].chip,
                    selectedColor === color ? "scale-125 border-strong" : "border-transparent",
                  )}
                />
              ))}

              <div className="h-4 w-px bg-subtle mx-1" />

              <Button
                size="sm"
                variant="primary"
                onClick={() =>
                  addHighlight.mutate({
                    text: selectionPopup.text,
                    note: highlightNote || undefined,
                    color: selectedColor,
                  })
                }
              >
                <Highlighter size={13} />
                <span>Vurgula</span>
              </Button>

              <IconButton
                title="Flashcard yap"
                onClick={handleConvertSelectionToFlashcard}
              >
                <Layers size={14} />
              </IconButton>

              <IconButton
                title="Gorev yap"
                onClick={handleConvertSelectionToTodo}
              >
                <CheckSquare size={14} />
              </IconButton>

              <IconButton
                title="Iptal"
                onClick={() => setSelectionPopup(null)}
              >
                <X size={14} />
              </IconButton>
            </div>

            <Input
              value={highlightNote}
              onChange={setHighlightNote}
              placeholder="Kisisel not ekle (istege bagli)..."
              className="text-meta"
            />
          </div>
        )}
      </div>
    </div>
  );
}
