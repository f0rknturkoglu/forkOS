import { useEffect, useRef, useState } from "react";
import { MoreHorizontal, Trash2 } from "lucide-react";
import type { MediaItem } from "@/core/types";
import { cx } from "@/core/ui";
import { externalLinks } from "./shared";

type MediaActionsMenuItem = Pick<
  MediaItem,
  "id" | "title" | "kind" | "meta" | "provider" | "provider_id" | "provider_ids"
>;

export function MediaActionsMenu({
  item,
  onTrash,
  disabled,
}: {
  item: MediaActionsMenuItem;
  onTrash: (item: MediaActionsMenuItem) => void;
  disabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const closeForEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      triggerRef.current?.focus();
    };
    const closeForOutsidePointer = (event: PointerEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (menuRef.current?.contains(target) || triggerRef.current?.contains(target)) return;
      setOpen(false);
    };

    document.addEventListener("keydown", closeForEscape);
    document.addEventListener("pointerdown", closeForOutsidePointer);
    return () => {
      document.removeEventListener("keydown", closeForEscape);
      document.removeEventListener("pointerdown", closeForOutsidePointer);
    };
  }, [open]);

  const links = externalLinks(
    item.kind,
    item.title,
    item.meta ?? {},
    item.provider,
    item.provider_id,
    item.provider_ids,
  );

  return (
    <div className="relative shrink-0">
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`${item.title} işlemleri`}
        onClick={() => setOpen((value) => !value)}
        className="flex h-8 w-8 items-center justify-center rounded-control border border-subtle text-secondary transition hover:border-strong hover:text-primary"
      >
        <MoreHorizontal size={16} aria-hidden="true" />
      </button>
      {open && (
        <div
          ref={menuRef}
          role="group"
          aria-label={`${item.title} işlemleri menüsü`}
          className="absolute right-0 z-20 mt-1 w-52 rounded-control border border-subtle bg-surface p-1 shadow-lg"
        >
          {links.map(([name, url]) => (
            <a
              key={name}
              href={url}
              target="_blank"
              rel="noreferrer"
              onClick={() => setOpen(false)}
              className="block rounded px-2.5 py-1.5 text-body text-secondary transition hover:bg-surface-hover hover:text-primary"
            >
              {name} ↗
            </a>
          ))}
          <div className="my-1 border-t border-subtle" />
          <button
            type="button"
            disabled={disabled}
            onClick={() => {
              setOpen(false);
              onTrash(item);
            }}
            className={cx(
              "flex w-full items-center gap-2 rounded px-2.5 py-1.5 text-left text-body text-danger transition hover:bg-danger-surface disabled:cursor-not-allowed disabled:opacity-50",
            )}
          >
            <Trash2 size={14} aria-hidden="true" />
            Çöpe taşı
          </button>
        </div>
      )}
    </div>
  );
}
