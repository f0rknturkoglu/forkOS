import { AlertTriangle } from "lucide-react";
import { useMemo } from "react";
import { useSourceHealth } from "@/core/runtimeQueries";
import { SectionFallback, dataState } from "@/core/DataState";
import { formatSourceDiagnostics, type SourceProblemDiagnostic } from "@/core/diagnostics";
import { runStateView } from "@/core/sourceStatus";
import { Chip, CopyButton, Empty, MiniStat, Section, relativeTime } from "@/core/ui";
import { sourceLabel } from "@/core/labels";
import type { SourceHealth } from "@/core/types";

/** `/sources/health` satiri bir kosu kaydidir; kapsam alanlari varsa tasinir. */
function toDiagnostic(run: SourceHealth): SourceProblemDiagnostic {
  const scope = run as SourceHealth & {
    error_kind?: string | null;
    circuit_open?: boolean | null;
    consecutive_failures?: number | null;
  };
  return {
    source: run.source,
    label: sourceLabel(run.source),
    status: run.status,
    error_kind: scope.error_kind ?? null,
    circuit_open: scope.circuit_open ?? null,
    consecutive_failures: scope.consecutive_failures ?? null,
    last_run_at: run.started_at,
    last_error: run.error,
  };
}

/**
 * Tum scraper/feed kaynaklarinin son kosum durumu (RSS dahil -- source_run).
 *
 * Durustluk: sorgu duserken/yuklenirken bu kart "saglikli" DEMEZ ve sahte sifir
 * gostermez. Tek `empty` kosu bilgilendirmedir, `disabled` notr; ikisi de
 * "ilgi isteyen" sayilmaz (bkz. @/core/sourceStatus).
 */
export function SourceHealthWidget() {
  // Kabuktaki paylasilan saglik sorgusu (bkz. core/runtimeQueries).
  const query = useSourceHealth();
  const state = dataState(query);
  const runs = query.data ?? [];

  const healthy = runs.filter((run) => run.status === "ok").length;
  // Ilgi isteyen = hata / kismi / yarim kaldi. Bos kosu ve kapali kaynak degil.
  const attention = runs.filter((run) => runStateView(run.status).attention);
  const empty = runs.filter((run) => run.status === "empty").length;
  const disabled = runs.filter((run) => run.status === "disabled").length;
  // Tanilama paketi yalniz BILINEN durumda kaynak sayisi yazar; hata/hazirlikta
  // "unknown sections" listelenir, uydurma sayi verilmez.
  const known = state === "ready" || state === "empty";

  /**
   * Agent'a yapistirilacak Markdown tanilama paketi (@/core/diagnostics).
   * Panoya yazma paylasilan CopyButton primitifinin isidir: burada yalniz
   * icerik ve baglama ozgu bildirim metni uretilir.
   */
  // Damga mount basina sabittir: her render'da degisen bir paket kopyalanmasin.
  const generatedAt = useMemo(() => new Date().toISOString(), []);
  const bundle = formatSourceDiagnostics({
    generated_at: generatedAt,
    scope: "kaynak sağlığı (son koşular, /sources/health)",
    source_count: known ? runs.length : null,
    problems: attention.map(toDiagnostic),
    unknown: known ? [] : ["sources"],
  });
  const bundleToast = known
    ? `${attention.length} kaynak sorunu panoya kopyalandı.`
    : "Kaynak sağlığı bilinmiyor: bilinmeyen durumu işaretleyen tanılama paketi kopyalandı.";

  return (
    <Section
      title="Kaynak Sağlığı"
      action={
        <div className="flex shrink-0 items-center gap-2">
          <CopyButton
            text={bundle}
            label="Tanılamayı kopyala"
            ariaLabel="Tanılamayı kopyala"
            disabled={state === "loading"}
            toastLabel={bundleToast}
            toastTone={known ? "ok" : "warn"}
          />
          <a href="#/sources" className="text-meta text-accent hover:underline">
            tüm kaynaklar →
          </a>
        </div>
      }
      bodyClassName="stack-y-4"
    >
      {state === "ready" ? (
        <>
          <div className="grid grid-cols-3 gap-3">
            <MiniStat label="Kaynak" value={runs.length} />
            <MiniStat label="Sağlıklı" value={healthy} tone="ok" />
            <MiniStat label="İlgi isteyen" value={attention.length} tone={attention.length > 0 ? "warn" : undefined} />
          </div>

          {attention.length === 0 ? (
            <Empty>
              {healthy === runs.length ? "Bütün kaynaklar son koşumda sağlıklı görünüyor." : "İlgi isteyen kaynak yok."}
            </Empty>
          ) : (
            <div>
              <p className="mb-2 text-meta text-secondary">
                <strong className="font-medium text-warn">{attention.length}</strong> kaynak ilgi istiyor:
              </p>
              <ul className="stack-y-2">
                {attention.slice(0, 8).map((run) => {
                  const view = runStateView(run.status);
                  return (
                    <li
                      key={`${run.source}-${run.started_at}`}
                      className="flex items-start gap-2.5 border-b border-danger-border bg-danger-surface px-3 py-2 last:border-b-0"
                    >
                      <AlertTriangle size={14} aria-hidden className="mt-0.5 shrink-0 text-danger" />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="truncate text-body text-primary">{sourceLabel(run.source)}</span>
                          <Chip tone={view.tone}>{view.label}</Chip>
                        </div>
                        {run.error && <p className="mt-0.5 truncate text-meta text-danger">{run.error}</p>}
                        <p className="mt-0.5 text-meta text-muted">{relativeTime(run.started_at)}</p>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {(empty > 0 || disabled > 0) && (
            <p className="text-meta text-muted">
              {[
                empty > 0 ? `${empty} kaynak son koşumda yeni kayıt bulamadı` : null,
                disabled > 0 ? `${disabled} kaynak kapalı` : null,
              ]
                .filter(Boolean)
                .join(" · ")}
              {" — bilgilendirme, sorun değil."}
            </p>
          )}
        </>
      ) : state === "empty" ? (
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
