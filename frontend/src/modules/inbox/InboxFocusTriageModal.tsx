import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Archive,
  BookOpen,
  Check,
  CheckSquare,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileText,
  Folder,
  GraduationCap,
  Pencil,
  StickyNote,
  Trash2,
  X,
} from "lucide-react";
import { api, qs } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { openObsidianUri, type VaultItem } from "@/core/obsidian";
import { Button, Chip, Empty, IconButton, Input, Kbd, Modal, cx, hostOf, relativeTime, useToast } from "@/core/ui";
import type { Bookmark, Collection } from "@/core/types";

interface InboxFocusTriageModalProps {
  open: boolean;
  onClose: () => void;
}

export function InboxFocusTriageModal({ open, onClose }: InboxFocusTriageModalProps) {
  const toast = useToast();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");

  const {
    data: items = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["bookmarks", "inbox", "triage-modal"],
    queryFn: () => api.get<Bookmark[]>(`/bookmarks${qs({ collection: "inbox", limit: 200 })}`),
    enabled: open,
  });

  const currentItem: Bookmark | undefined = items[currentIndex] ?? items[0];

  useEffect(() => {
    if (currentItem) {
      setTitleDraft(currentItem.title || currentItem.url);
      setEditingTitle(false);
    }
  }, [currentItem?.id]);

  useEffect(() => {
    if (items.length > 0 && currentIndex >= items.length) {
      setCurrentIndex(Math.max(0, items.length - 1));
    }
  }, [items.length, currentIndex]);

  const move = useMutation({
    mutationFn: ({ id, collection }: { id: string; collection: Collection }) =>
      api.patch(`/bookmarks/${id}/collection${qs({ collection })}`),
    onSuccess: (_, variables) => {
      invalidateAfter("bookmark.write");
      toast.push(`Kayit ${variables.collection} icine tasindi`, { tone: "ok" });
      refetch();
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/bookmarks/${id}`),
    onSuccess: () => {
      invalidateAfter("bookmark.write");
      toast.push("Kayit silindi", { tone: "neutral" });
      refetch();
    },
  });

  const convertToTask = useMutation({
    mutationFn: (id: string) => api.post<{ todo_id: string }>(`/bookmarks/${id}/convert-to-task`, { priority: 2 }),
    onSuccess: () => {
      invalidateAfter("bookmark.write", "todo.write", "link.write");
      toast.push("Goreve donusturuldu ve arsivlendi", { tone: "ok" });
      refetch();
    },
  });

  // Kanonik bilgi notu: kayit sahibi bookmark'tir, Vault dosyasini sunucu
  // uretir ve biz yalniz Obsidian'da acariz (forkOS'ta not editoru kalmadi).
  const createNote = useMutation({
    mutationFn: (id: string) => api.post<VaultItem>(`/bookmarks/${id}/source-note`),
    onSuccess: (item) => {
      invalidateAfter("bookmark.write", "obsidian.write");
      toast.push("Vault notu olusturuldu", { tone: "ok" });
      openObsidianUri(item.open_uri);
    },
  });

  const updateTitle = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) => api.patch(`/bookmarks/${id}`, { title }),
    onSuccess: () => {
      invalidateAfter("bookmark.write");
      setEditingTitle(false);
      toast.push("Baslik guncellendi", { tone: "ok" });
      refetch();
    },
  });

  // Klavye kisayollari
  useEffect(() => {
    if (!open || !currentItem || editingTitle) return;

    function onKeyDown(e: KeyboardEvent) {
      // Input odaktaysa tuslari yutma
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) return;
      if (!currentItem) return;

      const key = e.key.toLowerCase();

      if (key === "1" || key === "a") {
        e.preventDefault();
        move.mutate({ id: currentItem.id, collection: "archive" });
      } else if (key === "2" || key === "r") {
        e.preventDefault();
        move.mutate({ id: currentItem.id, collection: "read_later" });
      } else if (key === "3" || key === "t") {
        e.preventDefault();
        convertToTask.mutate(currentItem.id);
      } else if (key === "4" || key === "n") {
        e.preventDefault();
        createNote.mutate(currentItem.id);
      } else if (key === "5" || key === "l") {
        e.preventDefault();
        move.mutate({ id: currentItem.id, collection: "learning" });
      } else if (key === "6" || key === "p") {
        e.preventDefault();
        move.mutate({ id: currentItem.id, collection: "projects" });
      } else if (key === "backspace" || key === "d") {
        e.preventDefault();
        remove.mutate(currentItem.id);
      } else if (key === "arrowright" || key === "j") {
        e.preventDefault();
        setCurrentIndex((i) => Math.min(items.length - 1, i + 1));
      } else if (key === "arrowleft" || key === "k") {
        e.preventDefault();
        setCurrentIndex((i) => Math.max(0, i - 1));
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, currentItem, editingTitle, items.length]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Gelen Kutusu Ayiklama (Triage Modu)"
      hint={items.length > 0 ? `${currentIndex + 1} / ${items.length} bekleyen kayit` : undefined}
      className="max-w-2xl"
      footer={
        <div className="flex w-full items-center justify-between gap-2 text-meta text-muted">
          <div className="flex items-center gap-1.5">
            <span>Gezin:</span>
            <Kbd>J</Kbd>
            <Kbd>K</Kbd>
          </div>
          <Button size="sm" onClick={onClose}>
            Kapat
          </Button>
        </div>
      }
    >
      {isLoading ? (
        <div className="py-12 text-center text-meta text-muted">Kayitlar yukleniyor...</div>
      ) : items.length === 0 ? (
        <div className="py-8 text-center space-y-3">
          <Empty title="Gelen kutusu temiz">Tebrikler, bekleyen tum kayitlar ayiklandi. Gelen kutusu sifirlandi.</Empty>
          <Button variant="primary" onClick={onClose}>
            Bugun Paneline Don
          </Button>
        </div>
      ) : currentItem ? (
        <div className="space-y-4">
          {/* Kart govdesi */}
          <div className="rounded-card border border-strong bg-surface p-4 shadow-sm space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                {editingTitle ? (
                  <form
                    className="flex items-center gap-2"
                    onSubmit={(e) => {
                      e.preventDefault();
                      if (titleDraft.trim()) {
                        updateTitle.mutate({ id: currentItem.id, title: titleDraft.trim() });
                      }
                    }}
                  >
                    <Input
                      autoFocus
                      value={titleDraft}
                      onChange={setTitleDraft}
                      className="flex-1"
                      placeholder="Baslik"
                    />
                    <Button type="submit" variant="primary" size="sm">
                      <Check size={14} />
                    </Button>
                    <Button size="sm" onClick={() => setEditingTitle(false)}>
                      <X size={14} />
                    </Button>
                  </form>
                ) : (
                  <div className="flex items-baseline gap-2">
                    <h3 className="text-title font-medium text-primary break-words">
                      {currentItem.title || currentItem.url}
                    </h3>
                    <IconButton title="Basligi duzenle" onClick={() => setEditingTitle(true)}>
                      <Pencil size={13} />
                    </IconButton>
                  </div>
                )}

                <div className="mt-1 flex flex-wrap items-center gap-2 text-meta text-muted">
                  <span className="font-mono">{hostOf(currentItem.url)}</span>
                  <span>·</span>
                  <span>{relativeTime(currentItem.saved_at)}</span>
                  <Chip>{currentItem.source}</Chip>
                  {currentItem.is_duplicate && (
                    <Chip tone="warn">Zaten kayitli: {currentItem.existing_collection || "kutuphane"}</Chip>
                  )}
                  {currentItem.tags.map((tag) => (
                    <Chip key={tag}>#{tag}</Chip>
                  ))}
                </div>
              </div>

              <a
                href={currentItem.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-meta text-accent hover:underline shrink-0"
              >
                <span>Baglantiyi ac</span>
                <ExternalLink size={13} />
              </a>
            </div>

            {/* Kisisel Not (Hata duzeltmesi) */}
            {currentItem.note && (
              <div className="flex items-start gap-2 rounded-control border border-subtle bg-surface-sunken p-3 text-body text-primary">
                <StickyNote size={15} className="mt-0.5 shrink-0 text-muted" />
                <div className="min-w-0 flex-1">
                  <p className="text-meta font-medium text-secondary">Kisisel Not:</p>
                  <p className="mt-0.5 whitespace-pre-line text-meta">{currentItem.note}</p>
                </div>
              </div>
            )}

            {/* Secili Alinti */}
            {currentItem.selection && (
              <div className="border-l-2 border-accent pl-3 py-1 text-meta italic text-secondary">
                <p>"{currentItem.selection}"</p>
              </div>
            )}
          </div>

          {/* Ayiklama Aksiyon Butonlari */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => move.mutate({ id: currentItem.id, collection: "archive" })}
              className="flex items-center justify-between p-2.5 rounded-control border border-strong bg-surface hover:bg-surface-hover transition text-left"
            >
              <div className="flex items-center gap-2">
                <Archive size={15} className="text-muted" />
                <span className="text-body font-medium">Arsivle</span>
              </div>
              <Kbd>1</Kbd>
            </button>

            <button
              type="button"
              onClick={() => move.mutate({ id: currentItem.id, collection: "read_later" })}
              className="flex items-center justify-between p-2.5 rounded-control border border-strong bg-surface hover:bg-surface-hover transition text-left"
            >
              <div className="flex items-center gap-2">
                <BookOpen size={15} className="text-muted" />
                <span className="text-body font-medium">Sonra Oku</span>
              </div>
              <Kbd>2</Kbd>
            </button>

            <button
              type="button"
              onClick={() => convertToTask.mutate(currentItem.id)}
              className="flex items-center justify-between p-2.5 rounded-control border border-strong bg-surface hover:bg-surface-hover transition text-left"
            >
              <div className="flex items-center gap-2">
                <CheckSquare size={15} className="text-accent" />
                <span className="text-body font-medium text-accent">Gorev Yap</span>
              </div>
              <Kbd>3</Kbd>
            </button>

            <button
              type="button"
              onClick={() => createNote.mutate(currentItem.id)}
              className="flex items-center justify-between p-2.5 rounded-control border border-strong bg-surface hover:bg-surface-hover transition text-left"
            >
              <div className="flex items-center gap-2">
                <FileText size={15} className="text-muted" />
                <span className="text-body font-medium">Not Olustur</span>
              </div>
              <Kbd>4</Kbd>
            </button>

            <button
              type="button"
              onClick={() => move.mutate({ id: currentItem.id, collection: "learning" })}
              className="flex items-center justify-between p-2.5 rounded-control border border-strong bg-surface hover:bg-surface-hover transition text-left"
            >
              <div className="flex items-center gap-2">
                <GraduationCap size={15} className="text-muted" />
                <span className="text-body font-medium">Ogrenme</span>
              </div>
              <Kbd>5</Kbd>
            </button>

            <button
              type="button"
              onClick={() => move.mutate({ id: currentItem.id, collection: "projects" })}
              className="flex items-center justify-between p-2.5 rounded-control border border-strong bg-surface hover:bg-surface-hover transition text-left"
            >
              <div className="flex items-center gap-2">
                <Folder size={15} className="text-muted" />
                <span className="text-body font-medium">Projeler</span>
              </div>
              <Kbd>6</Kbd>
            </button>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-subtle">
            <div className="flex items-center gap-1">
              <IconButton
                title="Onceki kayit"
                disabled={currentIndex === 0}
                onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
              >
                <ChevronLeft size={16} />
              </IconButton>
              <IconButton
                title="Sonraki kayit"
                disabled={currentIndex >= items.length - 1}
                onClick={() => setCurrentIndex((i) => Math.min(items.length - 1, i + 1))}
              >
                <ChevronRight size={16} />
              </IconButton>
            </div>

            <Button variant="danger" size="sm" onClick={() => remove.mutate(currentItem.id)}>
              <Trash2 size={13} />
              <span>Cope At (D)</span>
            </Button>
          </div>
        </div>
      ) : null}
    </Modal>
  );
}
