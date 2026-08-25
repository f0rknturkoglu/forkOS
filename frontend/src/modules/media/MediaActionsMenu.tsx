import { useEffect, useId, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { MoreHorizontal, Trash2 } from "lucide-react";
import type { MediaItem } from "@/core/types";
import { cx } from "@/core/ui";
import { externalLinks } from "./shared";

type MediaActionsMenuItem = Pick<
  MediaItem,
  "id" | "title" | "kind" | "meta" | "provider" | "provider_id" | "provider_ids"
>;

type MenuPosition = { left: number; top: number; width: number; maxHeight?: number };

function menuPosition(triggerRect: DOMRect, menuRect: DOMRect, viewportWidth: number, viewportHeight: number): MenuPosition {
  const gutter = 8;
  const gap = 4;
  const width = Math.min(208, Math.max(0, viewportWidth - gutter * 2));
  const maxLeft = Math.max(gutter, viewportWidth - width - gutter);
  const belowTop = triggerRect.bottom + gap;
  const aboveTop = triggerRect.top - gap - menuRect.height;
  const belowFits = belowTop + menuRect.height <= viewportHeight - gutter;
  const aboveFits = aboveTop >= gutter;
  const top = belowFits ? belowTop : aboveFits ? aboveTop : gutter;
  return {
    width,
    left: Math.min(maxLeft, Math.max(gutter, triggerRect.right - width)),
    top,
    ...(!belowFits && !aboveFits ? { maxHeight: Math.max(0, viewportHeight - gutter * 2) } : {}),
  };
}

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
  const [position, setPosition] = useState<MenuPosition | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  const enabledMenuitems = () => Array.from(
    menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [],
  ).filter((element) => !(element instanceof HTMLButtonElement && element.disabled));

  const updatePosition = () => {
    const trigger = triggerRef.current;
    const menu = menuRef.current;
    if (!trigger || !menu) return;
    setPosition(menuPosition(
      trigger.getBoundingClientRect(),
      menu.getBoundingClientRect(),
      window.innerWidth,
      window.innerHeight,
    ));
  };

  useEffect(() => {
    if (!open) return;

    enabledMenuitems()[0]?.focus();
    updatePosition();

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
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      document.removeEventListener("keydown", closeForEscape);
      document.removeEventListener("pointerdown", closeForOutsidePointer);
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open]);

  const moveMenuFocus = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    const items = enabledMenuitems();
    if (!items.length) return;
    const index = items.indexOf(document.activeElement as HTMLElement);
    let nextIndex: number | null = null;
    if (event.key === "ArrowDown") nextIndex = (index + 1 + items.length) % items.length;
    if (event.key === "ArrowUp") nextIndex = (index - 1 + items.length) % items.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = items.length - 1;
    if (nextIndex === null) return;
    event.preventDefault();
    items[nextIndex].focus();
  };

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
        aria-controls={menuId}
        aria-label={`${item.title} işlemleri`}
        onClick={() => {
          if (open) {
            setOpen(false);
            return;
          }
          setPosition(null);
          setOpen(true);
        }}
        className="flex h-8 w-8 items-center justify-center rounded-control border border-subtle text-secondary transition hover:border-strong hover:text-primary"
      >
        <MoreHorizontal size={16} aria-hidden="true" />
      </button>
      {open && (
        <div
          ref={menuRef}
          id={menuId}
          role="menu"
          aria-label={`${item.title} işlemleri menüsü`}
          onKeyDown={moveMenuFocus}
          className="fixed z-20 rounded-control border border-subtle bg-surface p-1 shadow-lg"
          style={position ? {
            left: position.left,
            top: position.top,
            width: position.width,
            ...(position.maxHeight === undefined ? {} : { maxHeight: position.maxHeight, overflowY: "auto" }),
          } : undefined}
        >
          {links.map(([name, url]) => (
            <a
              key={name}
              href={url}
              role="menuitem"
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
            role="menuitem"
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
