import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { api } from "@/core/api";
import { Badge, Button, Empty, Section as Panel, cx, relativeTime, useToast } from "@/core/ui";
import { Copy } from "lucide-react";
import type { SourceHealth } from "@/core/types";
import { sourceLabel } from "@/modules/opportunity/labels";

function MiniStat({ label, value, tone }: { label: string; value: number; tone?: "ok" | "danger" }) {
  return (
    <div className="border-y border-subtle px-3 py-2">
      <div className={cx(
        "numeral text-[22px] leading-tight",
        tone === "ok" ? "text-ok" : tone === "danger" ? "text-danger" : "text-primary",
      )}>
        {value}
      </div>
      <div className="text-meta text-secondary">{label}</div>
    </div>
  );
}

/** Tum scraper/feed kaynaklarinin son kosum durumu (RSS dahil -- source_run). */
export function SourceHealthWidget() {
  const { data = [] } = useQuery({
    queryKey: ["sources", "health", "all"],
    queryFn: () => api.get<SourceHealth[]>("/sources/health?limit=2000"),
    refetchInterval: 60_000,
  });

  const tally = { ok: 0, empty: 0, error: 0 };
  for (const run of data) {
    if (run.status in tally) tally[run.status as keyof typeof tally] += 1;
  }
  const broken = data.filter((run) => run.status === "error");
  const toast = useToast();

  /** Agent'a yapistirmak icin hata satirlarini TSV olarak panoya kopyala. */
  async function copyErrors() {
    const text = broken
      .map((run) => [
        sourceLabel(run.source),
        run.status,
        run.error ?? "",
        new Date(run.started_at).toISOString(),
      ].join("	"))
      .join("\n");
    try {
      await navigator.clipboard.writeText(text || "hata yok");
      toast.push(`${broken.length} hata panoya kopyalandı`, { tone: "ok" });
    } catch {
      toast.push("Pano erişilemedi — tarayıcı izni gerekiyor.", { tone: "warn" });
    }
  }

  return (
    <Panel
      title="Kaynak Sağlığı"
      action={
        <div className="flex shrink-0 items-center gap-2">
          <Button size="sm" onClick={copyErrors} disabled={broken.length === 0} title="Hata satırlarını panoya kopyala (agent a yapistirmak icin)">
            <Copy size={13} /> Hataları kopyala
          </Button>
          <a href="#/sources" className="text-meta text-accent hover:underline">tüm kaynaklar →</a>
        </div>
      }
      bodyClassName="space-y-4"
    >
      <div className="grid grid-cols-3 gap-3">
        <MiniStat label="Kaynak" value={data.length} />
        <MiniStat label="Sağlıklı" value={tally.ok} tone="ok" />
        <MiniStat label="Hata" value={tally.error} tone="danger" />
      </div>

      {broken.length === 0 ? (
        <Empty>Bütün kaynaklar son koşumda sağlıklı görünüyor.</Empty>
      ) : (
        <div>
          <p className="mb-2 text-meta text-secondary">
            <strong className="font-medium text-danger">{broken.length}</strong> kaynak son koşumda hata verdi:
          </p>
          <ul className="space-y-2">
            {broken.slice(0, 8).map((run) => (
              <li
                key={run.source}
                className="flex items-start gap-2.5 border-b border-danger-border bg-danger-surface px-3 py-2 last:border-b-0"
              >
                <AlertTriangle size={14} className="mt-0.5 shrink-0 text-danger" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-body text-primary">{sourceLabel(run.source)}</span>
                    <Badge tone="danger">hata</Badge>
                  </div>
                  {run.error && <p className="mt-0.5 truncate text-meta text-danger">{run.error}</p>}
                  <p className="mt-0.5 text-meta text-muted">{relativeTime(run.started_at)}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}
