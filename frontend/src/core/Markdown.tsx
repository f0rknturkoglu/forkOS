/**
 * Markdown gorunumu -- ayristirici ciktisini React dugumune cevirir.
 *
 * HTML string URETMEZ; `dangerouslySetInnerHTML` hic kullanilmaz. Metin her
 * zaman React text node'u olarak basildigi icin not govdesi HTML/script
 * enjekte edemez. Baglantilar `safeHref` suzgecinden gecer.
 */
import { useEffect, useRef, useState, type ReactNode } from "react";
import { entityRoute } from "./entityRegistry";
import { parseMarkdown, safeHref, type Block, type Inline } from "./markdownParser";
import { Button, cx } from "./ui";

interface MarkdownProps {
  source: string;
  /** Cozulen [[hedef]] -> kayit. Tiklayinca dogrudan oraya gidilir. */
  links?: { target: string; id: string; type: string }[];
  /** Cozulemeyen (henuz olmayan) hedefler; kesik alti cizili ve soluk. */
  unresolved?: string[];
  /** Cozulemeyen bir hedefe tiklanirsa -- ornegin "bu baslikla not olustur". */
  onMissingClick?: (target: string) => void;
  onTagClick?: (name: string) => void;
  /** Gorev listesindeki satiri yerel not govdesinde isaretler. */
  onTaskToggle?: (line: number, checked: boolean) => void;
  className?: string;
}

function renderInline(nodes: Inline[], props: MarkdownProps, keyPrefix: string): ReactNode[] {
  const unresolved = new Set((props.unresolved ?? []).map((t) => t.toLocaleLowerCase("tr")));
  return nodes.map((node, index) => {
    const key = `${keyPrefix}-${index}`;
    switch (node.t) {
      case "text":
        return <span key={key}>{node.v}</span>;
      case "code":
        return (
          <code key={key} className="rounded-control bg-surface-sunken px-1 py-0.5 font-mono text-meta">
            {node.v}
          </code>
        );
      case "strong":
        return <strong key={key}>{renderInline(node.v, props, key)}</strong>;
      case "em":
        return <em key={key}>{renderInline(node.v, props, key)}</em>;
      case "strike":
        return (
          <span key={key} className="line-through text-muted">
            {renderInline(node.v, props, key)}
          </span>
        );
      case "mark":
        return (
          <mark key={key} className="rounded-control bg-warn-surface px-0.5 text-primary">
            {renderInline(node.v, props, key)}
          </mark>
        );
      case "link": {
        const href = safeHref(node.href);
        if (!href) return <span key={key}>{node.label}</span>;
        return (
          <a
            key={key}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent underline underline-offset-2"
          >
            {node.label}
          </a>
        );
      }
      case "image":
        // Local-only: Markdown bir dis URL'yi sessizce yukleyip veri sizdirmasin.
        // Yerel ek deposu legacy Notlar'la birlikte kalkti; bu yuzden resim
        // sozdizimi metin olarak gosterilir (uzak istek ATILMAZ).
        return (
          <span key={key}>
            ![{node.alt}]({node.src})
          </span>
        );
      case "wiki": {
        const hit = (props.links ?? []).find(
          (candidate) => candidate.target.toLocaleLowerCase("tr") === node.target.toLocaleLowerCase("tr"),
        );
        // Cozulmus hedef gercek bir baglantidir; cozulmemis olan tiklanabilir
        // ama farkli boyanir -- Obsidian'daki "olmayan not" gorunumu.
        if (hit) {
          return (
            <a
              key={key}
              href={`#${entityRoute(hit.type, hit.id)}`}
              title={node.target}
              className="rounded-control px-0.5 text-accent underline underline-offset-2 transition hover:bg-surface-hover"
            >
              {node.label}
            </a>
          );
        }
        const missing = unresolved.has(node.target.toLocaleLowerCase("tr")) || !hit;
        return (
          <button
            key={key}
            type="button"
            title={missing ? `"${node.target}" henüz yok` : node.target}
            onClick={() => props.onMissingClick?.(node.target)}
            className="rounded-control px-0.5 text-muted underline decoration-dashed underline-offset-2 transition hover:bg-surface-hover"
          >
            {node.label}
          </button>
        );
      }
      case "tag":
        return (
          <button
            key={key}
            type="button"
            onClick={() => props.onTagClick?.(node.name)}
            className="rounded-control px-0.5 text-accent transition hover:bg-surface-hover"
          >
            #{node.name}
          </button>
        );
    }
  });
}

const HEADING_CLASS: Record<number, string> = {
  1: " text-title text-primary",
  2: " text-heading text-primary",
  3: "text-heading text-primary",
  4: "text-body font-medium text-primary",
  5: "text-body font-medium text-secondary",
  6: "text-meta font-medium text-secondary",
};

function renderBlock(block: Block, props: MarkdownProps, key: string): ReactNode {
  switch (block.t) {
    case "heading": {
      const Tag = (["h1", "h2", "h3", "h4", "h5", "h6"] as const)[block.level - 1];
      return (
        <Tag key={key} className={cx("mt-4 first:mt-0", HEADING_CLASS[block.level])}>
          {renderInline(block.content, props, key)}
        </Tag>
      );
    }
    case "paragraph":
      return (
        <p key={key} className="text-body text-primary">
          {renderInline(block.content, props, key)}
        </p>
      );
    case "quote":
      return (
        <blockquote key={key} className="border-l-2 border-accent-border pl-3 text-body text-secondary">
          {block.content.map((row, index) => (
            <p key={index}>{renderInline(row, props, `${key}-${index}`)}</p>
          ))}
        </blockquote>
      );
    case "callout":
      return (
        <aside
          key={key}
          className="rounded-card border border-accent-border bg-surface-sunken px-3 py-2 text-body text-primary"
        >
          <p className="label-caps text-accent">{block.kind}</p>
          {block.content.map((row, index) => (
            <p key={index}>{renderInline(row, props, `${key}-${index}`)}</p>
          ))}
        </aside>
      );
    case "list": {
      const Tag = block.ordered ? "ol" : "ul";
      return (
        <Tag
          key={key}
          className={cx("ml-5 space-y-1 text-body text-primary", block.ordered ? "list-decimal" : "list-disc")}
        >
          {block.items.map((item, index) => (
            <li key={index}>{renderInline(item, props, `${key}-${index}`)}</li>
          ))}
        </Tag>
      );
    }
    case "tasks":
      return (
        <ul key={key} className="space-y-1 text-body text-primary">
          {block.items.map((item, index) => (
            <li key={index} className="flex items-start gap-2">
              {props.onTaskToggle ? (
                <Button
                  size="sm"
                  variant="ghost"
                  className={cx("mt-0.5 h-5 min-w-5 border-0 p-0", item.checked && "text-ok")}
                  aria-label={item.checked ? "Görevi yeniden aç" : "Görevi tamamla"}
                  onClick={() => props.onTaskToggle?.(item.line, !item.checked)}
                >
                  {item.checked ? "✓" : "□"}
                </Button>
              ) : (
                <span
                  aria-hidden
                  className={cx(
                    "mt-1 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-control border text-micro",
                    item.checked ? "border-ok bg-ok text-canvas" : "border-strong",
                  )}
                >
                  {item.checked ? "✓" : ""}
                </span>
              )}
              <span className={cx("min-w-0", item.checked && "text-muted line-through")}>
                {renderInline(item.content, props, `${key}-${index}`)}
              </span>
            </li>
          ))}
        </ul>
      );
    case "table":
      return (
        <div key={key} className="my-4 overflow-x-auto rounded-card border border-subtle bg-surface">
          <table className="w-full border-collapse text-left text-body text-primary">
            <thead className="bg-surface-sunken text-secondary">
              <tr>
                {block.header.map((cell, index) => (
                  <th
                    key={index}
                    scope="col"
                    className={cx(
                      "border-b border-subtle px-3 py-2 font-medium",
                      block.align[index] === "center" && "text-center",
                      block.align[index] === "right" && "text-right",
                    )}
                  >
                    {renderInline(cell, props, `${key}-h${index}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-subtle">
              {block.rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="transition hover:bg-surface-hover">
                  {row.map((cell, index) => (
                    <td
                      key={index}
                      className={cx(
                        "px-3 py-2 align-top",
                        block.align[index] === "center" && "text-center",
                        block.align[index] === "right" && "text-right",
                      )}
                    >
                      {renderInline(cell, props, `${key}-r${rowIndex}c${index}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    case "code":
      return (
        <pre
          key={key}
          className="overflow-x-auto rounded-card border border-subtle bg-surface-sunken p-3 font-mono text-meta text-primary"
        >
          <code>{block.v}</code>
        </pre>
      );
    case "hr":
      return <hr key={key} className="border-subtle" />;
  }
}

export function Markdown(props: MarkdownProps) {
  const blocks = parseMarkdown(props.source);
  if (blocks.length === 0) {
    return <p className="text-meta text-muted">Boş not.</p>;
  }
  return (
    <div className={cx("space-y-2.5", props.className)}>
      {blocks.map((block, index) => renderBlock(block, props, `b${index}`))}
    </div>
  );
}
