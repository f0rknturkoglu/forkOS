import { ChevronDown } from "lucide-react";
import { Badge, Empty, cx, relativeTime } from "@/core/ui";
import type { SourceHealth } from "@/core/types";

export interface SourceHealthAccordionProps {
  title?: string;
  sources: SourceHealth[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SourceHealthAccordion({
  title = "Kaynak Sağlığı",
  sources,
  open,
  onOpenChange,
}: SourceHealthAccordionProps): JSX.Element {
  const healthy = sources.filter((source) => source.status === "ok").length;
  const problematic = sources.filter((source) => source.status === "error").length;

  return (
    <details
      data-source-health
      open={open}
      onToggle={(event) => onOpenChange(event.currentTarget.open)}
      className="overflow-hidden rounded-card border border-subtle bg-surface shadow-card"
    >
      <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3 marker:content-none">
        <ChevronDown className={cx("transition-transform", open && "rotate-180")} size={15} />
        <span className="text-body font-medium text-primary">{title}</span>
        <span className="ml-auto text-meta text-muted">{sources.length} kayıt</span>
        {healthy > 0 && <Badge tone="ok">{healthy} sağlıklı</Badge>}
        {problematic > 0 && <Badge tone="warn">{problematic} sorunlu</Badge>}
      </summary>
      <div className="border-t border-subtle">
        {sources.length === 0 ? (
          <Empty>Kayıt yok.</Empty>
        ) : (
          <ul>
            {sources.map((source) => (
              <li
                key={`${source.source}-${source.started_at}`}
                className="grid gap-1 border-b border-subtle px-4 py-2.5 last:border-b-0 sm:grid-cols-[minmax(0,1fr)_auto_auto]"
              >
                <div className="min-w-0">
                  <p className="truncate text-body text-primary">{source.source}</p>
                  {source.error && <p className="truncate text-meta text-danger">{source.error}</p>}
                </div>
                <Badge tone={source.status === "ok" ? "ok" : source.status === "error" ? "danger" : "warn"}>
                  {source.status}
                </Badge>
                <span className="text-meta text-muted">+{source.items_found} · {relativeTime(source.started_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </details>
  );
}
