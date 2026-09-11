import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronRight, ListTodo, Timer } from "lucide-react";
import type { StudyTreeNode } from "@/core/types";
import { Chip, cx } from "@/core/ui";
import { reviewLabel, statusLabel, statusTone } from "./learningLabels";

/**
 * Konu agaci — 256+ dugumde DOM'a YALNIZ gorunur satirlar girer.
 *
 * Backend duz liste + `depth` + ata `path` dondurur; agac burada `parent_id`
 * ile kurulur. Varsayilan olarak yalniz kokler aciktir; `?focus=` konusunun
 * ata zinciri (`revealPath`) ve arama sonucu (`expandAll`) otomatik acilir.
 *
 * Erisilebilirlik: WAI-ARIA agac deseni (roving tabindex). Ok tuslari
 * gorunur ogeler arasinda gezer, Enter/Space secer.
 */

/** Derinlik -> girinti. Siniflar STATIK (Tailwind JIT kaynakta arar). */
const INDENT = ["pl-1", "pl-4", "pl-8", "pl-12", "pl-16", "pl-20"];

interface Row {
  node: StudyTreeNode;
  depth: number;
  childCount: number;
  isOpen: boolean;
}

/** Gorunur satirlari derler: kapali dalin cocuklari hic uretilmez. */
function flattenVisible(nodes: StudyTreeNode[], expanded: ReadonlySet<string>): Row[] {
  const ids = new Set(nodes.map((node) => node.id));
  const byParent = new Map<string | null, StudyTreeNode[]>();
  for (const node of nodes) {
    const parent = node.parent_id && ids.has(node.parent_id) ? node.parent_id : null;
    const bucket = byParent.get(parent);
    if (bucket) bucket.push(node);
    else byParent.set(parent, [node]);
  }
  const rows: Row[] = [];
  const seen = new Set<string>();
  const walk = (parent: string | null, depth: number) => {
    for (const node of byParent.get(parent) ?? []) {
      if (seen.has(node.id)) continue; // bozuk veri (dongu) sonsuz acmasin
      seen.add(node.id);
      const children = byParent.get(node.id) ?? [];
      rows.push({ node, depth, childCount: children.length, isOpen: expanded.has(node.id) });
      if (children.length > 0 && expanded.has(node.id)) walk(node.id, depth + 1);
    }
  };
  walk(null, 0);
  return rows;
}

/**
 * Baslangic katlanma durumu: kokler acik, derin baglanti atalari acik,
 * arama modunda tum sonuc dallari acik (eslesenler gorunur olsun).
 */
function initialExpanded(nodes: StudyTreeNode[], options: { expandAll: boolean; revealPath: string[] }): Set<string> {
  const ids = new Set(nodes.map((node) => node.id));
  const open = new Set<string>();
  const parents = new Set<string>();
  for (const node of nodes) {
    if (node.parent_id && ids.has(node.parent_id)) parents.add(node.parent_id);
  }
  if (options.expandAll) {
    for (const id of parents) open.add(id);
    return open;
  }
  for (const node of nodes) {
    if (!node.parent_id || !ids.has(node.parent_id)) open.add(node.id);
  }
  for (const id of options.revealPath) if (ids.has(id)) open.add(id);
  return open;
}

interface TopicTreeProps {
  nodes: StudyTreeNode[];
  selectedId: string;
  onSelect: (topicId: string) => void;
  /** Secili konunun atalari (derin baglanti zinciri acilir). */
  revealPath?: string[];
  /** Arama sonucu listesi: tum dallar acik gelir. */
  expandAll?: boolean;
  onTask?: (node: StudyTreeNode) => void;
  onFocusTopic?: (node: StudyTreeNode) => void;
  /** Cevrimdisi: yazma aksiyonlari gerekcesiyle kapali. */
  actionsDisabled?: boolean;
  ariaLabel?: string;
}

export function TopicTree({
  nodes,
  selectedId,
  onSelect,
  revealPath = [],
  expandAll = false,
  onTask,
  onFocusTopic,
  actionsDisabled = false,
  ariaLabel = "Konu ağacı",
}: TopicTreeProps) {
  const [expanded, setExpanded] = useState<Set<string>>(() => initialExpanded(nodes, { expandAll, revealPath }));
  const [activeId, setActiveId] = useState(selectedId);
  const items = useRef(new Map<string, HTMLDivElement>());
  const revealed = useRef("");

  const rows = useMemo(() => flattenVisible(nodes, expanded), [nodes, expanded]);

  // Derin baglanti atalari (odak degisince) acilir.
  const revealKey = revealPath.join(",");
  useEffect(() => {
    if (!revealKey) return;
    const ids = new Set(revealKey.split(","));
    setExpanded((prev) => {
      let changed = false;
      const next = new Set(prev);
      for (const id of ids) {
        if (!next.has(id)) {
          next.add(id);
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [revealKey]);

  useEffect(() => {
    if (selectedId) setActiveId(selectedId);
  }, [selectedId]);

  useEffect(() => {
    if (rows.length === 0) return;
    if (rows.some((row) => row.node.id === activeId)) return;
    setActiveId(rows[0].node.id);
  }, [rows, activeId]);

  // Secili satir gorunur alana gelir (media modulundeki desen).
  useEffect(() => {
    if (!selectedId) {
      revealed.current = "";
      return;
    }
    if (revealed.current === selectedId) return;
    const element = items.current.get(selectedId);
    if (!element) return;
    revealed.current = selectedId;
    element.scrollIntoView({ block: "nearest" });
    if (document.activeElement !== element) element.focus({ preventScroll: true });
  }, [selectedId, rows]);

  const toggle = useCallback((id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (rows.length === 0) return;
    const index = Math.max(
      0,
      rows.findIndex((row) => row.node.id === activeId),
    );
    const row = rows[index];
    const goTo = (target: number) => {
      const next = rows[target];
      if (!next) return;
      event.preventDefault();
      setActiveId(next.node.id);
      items.current.get(next.node.id)?.focus();
    };
    switch (event.key) {
      case "ArrowDown":
        return goTo(Math.min(index + 1, rows.length - 1));
      case "ArrowUp":
        return goTo(Math.max(index - 1, 0));
      case "Home":
        return goTo(0);
      case "End":
        return goTo(rows.length - 1);
      case "ArrowRight": {
        if (row.childCount === 0) return;
        if (!row.isOpen) {
          event.preventDefault();
          toggle(row.node.id);
          return;
        }
        return goTo(index + 1);
      }
      case "ArrowLeft": {
        if (row.childCount > 0 && row.isOpen) {
          event.preventDefault();
          toggle(row.node.id);
          return;
        }
        const parentIndex = rows.findIndex((item, position) => position < index && item.node.id === row.node.parent_id);
        if (parentIndex >= 0) return goTo(parentIndex);
        return;
      }
      case "Enter":
      case " ": {
        event.preventDefault();
        onSelect(row.node.id);
        return;
      }
      default:
    }
  };

  if (rows.length === 0) return null;

  return (
    <div role="tree" aria-label={ariaLabel} onKeyDown={onKeyDown} className="select-none">
      {rows.map(({ node, depth, childCount, isOpen }) => {
        const selected = node.id === selectedId;
        return (
          <div
            key={node.id}
            role="treeitem"
            data-tree-id={node.id}
            aria-level={depth + 1}
            aria-selected={selected}
            aria-expanded={childCount > 0 ? isOpen : undefined}
            tabIndex={node.id === activeId ? 0 : -1}
            ref={(element) => {
              if (element) items.current.set(node.id, element);
              else items.current.delete(node.id);
            }}
            className={cx(
              "group flex items-start gap-1 rounded-control pr-1 transition",
              INDENT[Math.min(depth, INDENT.length - 1)],
              selected ? "bg-accent-surface" : "hover:bg-surface-hover",
            )}
          >
            {childCount > 0 ? (
              <button
                type="button"
                aria-label={`${isOpen ? "Daralt" : "Genişlet"}: ${node.title}`}
                onClick={() => toggle(node.id)}
                className={cx(
                  "mt-1.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-control text-muted transition",
                  "hover:bg-surface-sunken hover:text-primary",
                )}
              >
                {isOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
              </button>
            ) : (
              <span aria-hidden="true" className="mt-1.5 h-6 w-6 shrink-0" />
            )}

            <button
              type="button"
              onClick={() => onSelect(node.id)}
              title={node.title}
              className="min-w-0 flex-1 py-1.5 text-left"
            >
              <span className={cx("block truncate text-body", selected ? "text-primary" : "text-secondary")}>
                {node.title}
              </span>
              <span className="mt-0.5 flex flex-wrap items-center gap-1.5">
                <Chip tone={statusTone(node.status)} size="xs">
                  {statusLabel(node.status)}
                </Chip>
                {node.resource_total > 0 && (
                  <span className="flex items-center gap-1">
                    <span
                      role="progressbar"
                      aria-label={`${node.title} kaynak ilerlemesi`}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={node.progress_pct}
                      className="h-1 w-10 overflow-hidden rounded-control bg-surface-sunken"
                    >
                      <span
                        className={cx(
                          "block h-full rounded-control",
                          node.progress_pct === 100 ? "bg-ok" : "bg-accent",
                        )}
                        style={{ width: `${node.progress_pct}%` }}
                      />
                    </span>
                    <span className="tabular-nums text-micro text-muted">
                      {node.resource_done}/{node.resource_total}
                    </span>
                  </span>
                )}
                {childCount > 0 && <span className="text-micro text-muted">{childCount} alt</span>}
                {node.review_due && (
                  <Chip tone="warn" size="xs">
                    <span title={reviewLabel(node.next_review_at, node.review_due)}>Tekrar</span>
                  </Chip>
                )}
              </span>
            </button>

            {/* Satir aksiyonlari hover'a bagli DEGIL: her zaman gorunur ve
                aria-label tasir (klavye ile de erisilir). */}
            <span className="mt-1.5 flex shrink-0 items-center gap-0.5">
              {onTask && (
                <button
                  type="button"
                  title="Görev oluştur"
                  aria-label={`"${node.title}" için görev oluştur`}
                  disabled={actionsDisabled}
                  onClick={() => onTask(node)}
                  className={cx(
                    "flex h-7 w-7 items-center justify-center rounded-control text-muted transition",
                    "hover:bg-surface-sunken hover:text-primary disabled:cursor-not-allowed disabled:opacity-40",
                  )}
                >
                  <ListTodo size={13} />
                </button>
              )}
              {onFocusTopic && (
                <button
                  type="button"
                  title="Odaklan"
                  aria-label={`"${node.title}" için odaklan`}
                  disabled={actionsDisabled}
                  onClick={() => onFocusTopic(node)}
                  className={cx(
                    "flex h-7 w-7 items-center justify-center rounded-control text-muted transition",
                    "hover:bg-surface-sunken hover:text-primary disabled:cursor-not-allowed disabled:opacity-40",
                  )}
                >
                  <Timer size={13} />
                </button>
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}
