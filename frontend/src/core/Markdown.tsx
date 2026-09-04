/**
 * Markdown gorunumu -- ayristirici ciktisini React dugumune cevirir.
 *
 * HTML string URETMEZ; `dangerouslySetInnerHTML` hic kullanilmaz. Metin her
 * zaman React text node'u olarak basildigi icin not govdesi HTML/script
 * enjekte edemez. Baglantilar `safeHref` suzgecinden gecer.
 */
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Download, File, FileAudio, FilePenLine, FileText, FileVideo, Pause, Play, Trash2 } from "lucide-react";
import { entityRoute } from "./entityRegistry";
import { parseMarkdown, safeHref, type Block, type Inline } from "./markdownParser";
import type { NoteAttachment } from "./types";
import { IconButton, Range, cx } from "./ui";

interface MarkdownProps {
  source: string;
  /** Cozulen [[hedef]] -> kayit. Tiklayinca dogrudan oraya gidilir. */
  links?: { target: string; id: string; type: string }[];
  /** Cozulemeyen (henuz olmayan) hedefler; kesik alti cizili ve soluk. */
  unresolved?: string[];
  /** Cozulemeyen bir hedefe tiklanirsa -- ornegin "bu baslikla not olustur". */
  onMissingClick?: (target: string) => void;
  onTagClick?: (name: string) => void;
  /** Nota ait yerel ekler; Markdown baglantilari medya olarak render edilir. */
  attachments?: NoteAttachment[];
  onRemoveAttachment?: (attachment: NoteAttachment) => void;
  className?: string;
}

function localAttachment(props: MarkdownProps, href: string): NoteAttachment | undefined {
  return props.attachments?.find((attachment) => attachment.url === href);
}

function attachmentActions(attachment: NoteAttachment, props: MarkdownProps, key: string) {
  if (!props.onRemoveAttachment) return null;
  return (
    <IconButton
      key={`${key}-remove`}
      title="Eki sil"
      tone="danger"
      onClick={() => props.onRemoveAttachment?.(attachment)}
    >
      <Trash2 size={13} />
    </IconButton>
  );
}

function formatDuration(value: number): string {
  if (!Number.isFinite(value) || value < 0) return "0:00";
  const minutes = Math.floor(value / 60);
  return `${minutes}:${Math.floor(value % 60)
    .toString()
    .padStart(2, "0")}`;
}

function LocalAudioPlayer({
  attachment,
  href,
  onRemove,
}: {
  attachment: NoteAttachment;
  href: string;
  onRemove?: (attachment: NoteAttachment) => void;
}) {
  const audio = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const element = audio.current;
    if (!element) return;
    const sync = () => setCurrent(element.currentTime || 0);
    const metadata = () => setDuration(Number.isFinite(element.duration) ? element.duration : 0);
    const stopped = () => setPlaying(false);
    element.addEventListener("timeupdate", sync);
    element.addEventListener("loadedmetadata", metadata);
    element.addEventListener("durationchange", metadata);
    element.addEventListener("ended", stopped);
    element.addEventListener("pause", stopped);
    return () => {
      element.removeEventListener("timeupdate", sync);
      element.removeEventListener("loadedmetadata", metadata);
      element.removeEventListener("durationchange", metadata);
      element.removeEventListener("ended", stopped);
      element.removeEventListener("pause", stopped);
    };
  }, []);

  const toggle = async () => {
    const element = audio.current;
    if (!element) return;
    if (element.paused) {
      await element.play();
      setPlaying(true);
    } else {
      element.pause();
    }
  };

  return (
    <span className="my-4 block overflow-hidden rounded-card border border-subtle bg-surface shadow-card">
      <audio ref={audio} preload="metadata" src={href} className="hidden" />
      <span className="flex items-center gap-3 px-3.5 py-3">
        <button
          type="button"
          onClick={() => void toggle()}
          aria-label={playing ? "Sesi duraklat" : "Sesi oynat"}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-canvas transition hover:opacity-80"
        >
          {playing ? <Pause size={16} /> : <Play size={16} className="translate-x-px" />}
        </button>
        <span className="min-w-0 flex-1">
          <span className="mb-1.5 flex items-center gap-2">
            <FileAudio size={14} className="shrink-0 text-icon" />
            <span className="min-w-0 flex-1 truncate text-meta font-medium text-primary">{attachment.name}</span>
            <span className="text-micro tabular-nums text-muted">
              {formatDuration(current)} / {formatDuration(duration)}
            </span>
          </span>
          <Range
            value={Math.min(current, duration || 0)}
            max={duration || 1}
            step={0.1}
            ariaLabel={`${attachment.name} oynatma konumu`}
            onChange={(value) => {
              if (audio.current) audio.current.currentTime = value;
              setCurrent(value);
            }}
          />
        </span>
        <a href={href} download={attachment.name} title="Sesi indir" className="text-icon hover:text-primary">
          <Download size={15} />
        </a>
        {onRemove && (
          <IconButton title="Eki sil" tone="danger" onClick={() => onRemove(attachment)}>
            <Trash2 size={13} />
          </IconButton>
        )}
      </span>
    </span>
  );
}

function attachmentIcon(mime: string) {
  if (mime.startsWith("video/")) return <FileVideo size={18} className="text-icon" />;
  if (mime === "application/pdf" || mime.startsWith("text/")) return <FileText size={18} className="text-icon" />;
  if (mime === "application/vnd.excalidraw+json") return <FilePenLine size={18} className="text-icon" />;
  return <File size={18} className="text-icon" />;
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
        const attachment = localAttachment(props, href);
        if (attachment?.mime.startsWith("audio/")) {
          return <LocalAudioPlayer key={key} attachment={attachment} href={href} onRemove={props.onRemoveAttachment} />;
        }
        if (attachment?.mime.startsWith("video/")) {
          return (
            <span
              key={key}
              className="my-4 block overflow-hidden rounded-card border border-subtle bg-surface shadow-card"
            >
              <video controls preload="metadata" src={href} className="max-h-screen w-full bg-surface-sunken" />
              <span className="flex items-center gap-2 border-t border-subtle px-3 py-2 text-meta text-muted">
                <FileVideo size={14} />
                <span className="min-w-0 flex-1 truncate">{attachment.name}</span>
                {attachmentActions(attachment, props, key)}
              </span>
            </span>
          );
        }
        if (attachment) {
          const kind =
            attachment.mime === "application/vnd.excalidraw+json"
              ? "Excalidraw"
              : attachment.mime === "application/pdf"
                ? "PDF"
                : "Dosya";
          return (
            <span
              key={key}
              className="my-3 flex items-center gap-3 rounded-card border border-subtle bg-surface px-3 py-2.5 shadow-card"
            >
              {attachmentIcon(attachment.mime)}
              <a href={href} target="_blank" rel="noopener noreferrer" className="min-w-0 flex-1">
                <span className="block truncate text-body font-medium text-primary">{attachment.name}</span>
                <span className="block text-meta text-muted">
                  {kind} · {Math.max(1, Math.round(attachment.size / 1024))} KB
                </span>
              </a>
              <a href={href} download={attachment.name} title="Dosyayı indir" className="text-icon hover:text-primary">
                <Download size={15} />
              </a>
              {attachmentActions(attachment, props, key)}
            </span>
          );
        }
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
      case "image": {
        // Local-only: Markdown bir dis URL'yi sessizce yukleyip veri sizdirmasin.
        const attachment = localAttachment(props, node.src);
        if (!attachment?.mime.startsWith("image/"))
          return (
            <span key={key}>
              ![{node.alt}]({node.src})
            </span>
          );
        return (
          <span key={key} className="my-3 block overflow-hidden rounded-card border border-subtle bg-surface">
            <img src={node.src} alt={node.alt} className="max-h-screen w-full object-contain" loading="lazy" />
            <span className="flex items-center gap-2 border-t border-subtle px-3 py-2">
              <span className="min-w-0 flex-1 truncate text-meta text-muted">{attachment.name}</span>
              {attachmentActions(attachment, props, key)}
            </span>
          </span>
        );
      }
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
              {/* Onizleme salt okunur: kutu govdedeki "- [x]" metnini yansitir. */}
              <span
                aria-hidden
                className={cx(
                  "mt-1 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-control border text-micro",
                  item.checked ? "border-ok bg-ok text-canvas" : "border-strong",
                )}
              >
                {item.checked ? "✓" : ""}
              </span>
              <span className={cx("min-w-0", item.checked && "text-muted line-through")}>
                {renderInline(item.content, props, `${key}-${index}`)}
              </span>
            </li>
          ))}
        </ul>
      );
    case "table":
      return (
        <div key={key} className="my-4 overflow-x-auto rounded-card border border-subtle bg-surface shadow-card">
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
