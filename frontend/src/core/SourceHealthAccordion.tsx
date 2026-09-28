import { ChevronDown } from "lucide-react";
import { runStateView } from "@/core/sourceStatus";
import { Chip, Empty, cx, relativeTime } from "@/core/ui";
import type { SourceHealth } from "@/core/types";

interface SourceHealthAccordionProps {
  title?: string;
  sources: SourceHealth[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Kosu satirlarinin katlanir listesi.
 *
 * Durustluk: chip etiketi ham `status` enum'u DEGIL, tek sozlukten
 * (@/core/sourceStatus) gelir. "Sorunlu" sayaci ok disi her seyi saymaz:
 * `empty` (yeni kayit yok) ve `disabled` (kullanici kapatti) sorun degildir;
 * yalniz `attention` isaretli kosular "ilgi istiyor" sayilir.
 */
export function SourceHealthAccordion({
  title = "Kaynak Sağlığı",
  sources,
  open,
  onOpenChange,
}: SourceHealthAccordionProps): JSX.Element {
  const healthy = sources.filter((source) => source.status === "ok").length;
  const attention = sources.filter((source) => runStateView(source.status).attention).length;

  return (
    <details
      data-source-health
      open={open}
      onToggle={(event) => onOpenChange(event.currentTarget.open)}
      className="overflow-hidden rounded-card border border-subtle bg-surface"
    >
      <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3 marker:content-none">
        <ChevronDown className={cx("transition-transform", open && "rotate-180")} aria-hidden size={15} />
        <span className="text-body font-medium text-primary">{title}</span>
        <span className="ml-auto text-meta text-muted">{sources.length} kayıt</span>
        {healthy > 0 && <Chip tone="ok">{healthy} sağlıklı</Chip>}
        {attention > 0 && <Chip tone="warn">{attention} ilgi istiyor</Chip>}
      </summary>
      <div className="border-t border-subtle">
        {sources.length === 0 ? (
          <Empty>Kayıt yok.</Empty>
        ) : (
          <ul>
            {sources.map((source) => {
              const view = runStateView(source.status);
              return (
                <li
                  key={`${source.source}-${source.started_at}`}
                  className="grid gap-1 border-b border-subtle px-4 py-2.5 last:border-b-0 sm:grid-cols-[minmax(0,1fr)_auto_auto]"
                >
                  <div className="min-w-0">
                    <p className="truncate text-body text-primary">{source.source}</p>
                    {source.error && <p className="truncate text-meta text-danger">{source.error}</p>}
                  </div>
                  <Chip tone={view.tone}>{view.label}</Chip>
                  <span className="text-meta text-muted">
                    +{source.items_found}
                    {typeof (source as { items_seen?: number }).items_seen === "number" &&
                    (source as { items_seen?: number }).items_seen! > 0 &&
                    (source as { items_seen?: number }).items_seen !== source.items_found
                      ? ` (${(source as { items_seen?: number }).items_seen} görüldü)`
                      : ""}
                    {" · "}
                    {relativeTime(source.started_at)}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </details>
  );
}
