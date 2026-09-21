import { AlertTriangle } from "lucide-react";
import { useSourceHealth } from "@/core/runtimeQueries";
import { SectionFallback, dataState } from "@/core/DataState";
import { runStateView } from "@/core/sourceStatus";
import { Empty, Section } from "@/core/ui";

/**
 * Kaynak sagligi ozeti (StatusLed ust seritte).
 *
 * Durustluk: sorgu duserken "Kaynaklar saglikli." DENMEZ; yuklenirken iskelet
 * gosterilir. Tek `empty` kosu ya da kapali kaynak SORUN sayilmaz -- yalniz
 * `attention` isaretli kosular (hata/kismi/yarim kaldi) listelenir.
 */
export function SourceHealthMiniWidget() {
  // Kabuktaki paylasilan saglik sorgusu: cekim surerken hizlanir, bosta seyrek.
  const query = useSourceHealth();
  const state = dataState(query);
  if (state !== "ready") {
    return (
      <Section title="Kaynak sağlığı">
        {state === "empty" ? (
          <SectionFallback state="empty" what="Kaynak sağlığı" emptyLabel="Kaynak koşu kaydı yok." />
        ) : (
          <SectionFallback
            state={state}
            what="Kaynak sağlığı"
            onRetry={() => {
              void query.refetch();
            }}
          />
        )}
      </Section>
    );
  }

  const runs = query.data ?? [];
  const attention = runs.filter((run) => runStateView(run.status).attention);
  const healthy = runs.filter((run) => run.status === "ok").length;
  const names = attention
    .slice(0, 3)
    .map((run) => run.source)
    .join(", ");
  return (
    <Section title="Kaynak sağlığı">
      {attention.length === 0 ? (
        <Empty>{healthy === runs.length ? "Kaynaklar sağlıklı." : "İlgi isteyen kaynak yok."}</Empty>
      ) : (
        <a href="#/health" className="flex items-center gap-2 text-meta text-danger hover:underline">
          <AlertTriangle size={13} aria-hidden className="shrink-0" />
          {attention.length} kaynak ilgi istiyor{names ? ` (${names}${attention.length > 3 ? "…" : ""})` : ""}
        </a>
      )}
    </Section>
  );
}
