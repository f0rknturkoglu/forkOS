import { useEffect, useState } from "react";

interface VirtualOptions {
  count: number;
  estimateSize?: number | (() => number);
  overscan?: number;
  getScrollElement: () => HTMLElement | null;
}

interface VirtualItem {
  index: number;
  start: number;
  size: number;
}

/**
 * Sıfır harici bağımlılık ile çalışan hafif sanallaştırma (virtual list) hook'u.
 * Yalnızca ekranda görünen öğeleri ve overscan tamponunu DOM'a bağlar.
 */
export function useVirtualizer({ count, estimateSize = 74, overscan = 5, getScrollElement }: VirtualOptions) {
  const [scrollTop, setScrollTop] = useState(0);
  const [clientHeight, setClientHeight] = useState(600);

  const resolvedSize = typeof estimateSize === "function" ? estimateSize() : estimateSize;

  useEffect(() => {
    const el = getScrollElement();
    if (!el) return;

    setScrollTop(el.scrollTop);
    setClientHeight(el.clientHeight || 600);

    const onScroll = () => {
      setScrollTop(el.scrollTop);
    };

    const resizeObserver =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver((entries) => {
            for (const entry of entries) {
              if (entry.target === el) {
                setClientHeight(el.clientHeight);
              }
            }
          })
        : null;

    el.addEventListener("scroll", onScroll, { passive: true });
    if (resizeObserver) resizeObserver.observe(el);

    return () => {
      el.removeEventListener("scroll", onScroll);
      if (resizeObserver) resizeObserver.disconnect();
    };
  }, [getScrollElement]);

  const totalSize = count * resolvedSize;
  const startIndex = Math.max(0, Math.floor(scrollTop / resolvedSize) - overscan);
  const endIndex = Math.min(count, Math.ceil((scrollTop + clientHeight) / resolvedSize) + overscan);

  const virtualItems: VirtualItem[] = [];
  for (let i = startIndex; i < endIndex; i++) {
    virtualItems.push({
      index: i,
      start: i * resolvedSize,
      size: resolvedSize,
    });
  }

  return {
    getTotalSize: () => totalSize,
    getVirtualItems: () => virtualItems,
    measureElement: () => {},
  };
}
