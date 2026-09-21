/**
 * Bölüm bazlı veri durumu — "bilinmiyor"u "sorun yok"tan ayırmak için.
 *
 * Kural (sağlık yüzeyinin en önemli dürüstlük maddesi):
 *   NO DATA ≠ HEALTHY · QUERY ERROR ≠ HEALTHY · UNKNOWN ≠ HEALTHY
 *
 * Bir sağlık sorgusu düştüğünde arayüz "her şey yolunda" cümlesi KURMAZ;
 * "alınamadı" der ve yeniden denemeyi teklif eder. Yükleme sırasında da sahte
 * sıfır/yeşil gösterilmez.
 */
import type { ReactNode } from "react";
import { Button, Empty, Skeleton, cx } from "./ui";
import { RefreshCw } from "lucide-react";

export type DataState = "loading" | "error" | "empty" | "ready";

/** TanStack Query benzeri her nesne için durum türetir (tip bağımsız). */
export function dataState(query: { isLoading?: boolean; isError?: boolean; data?: unknown }): DataState {
  if (query.isError) return "error";
  if (query.isLoading || query.data === undefined) return "loading";
  if (Array.isArray(query.data) && query.data.length === 0) return "empty";
  return "ready";
}

/**
 * Yükleme / hata / boş için ortak gösterim. Her bölüm KENDİ durumunu taşır:
 * bir uç düştüğünde yalnız o bölüm bunu söyler, sayfa çalışmaya devam eder.
 */
export function SectionFallback({
  state,
  what,
  onRetry,
  emptyLabel,
  className,
}: {
  state: Exclude<DataState, "ready">;
  /** "Kaynak kataloğu", "Yedek durumu" gibi bölüm adı. */
  what: string;
  onRetry?: () => void;
  emptyLabel?: ReactNode;
  className?: string;
}) {
  if (state === "loading") {
    return <Skeleton className={cx("h-16", className)} />;
  }
  if (state === "empty") {
    return <Empty>{emptyLabel ?? "Kayıt yok."}</Empty>;
  }
  return (
    <div className={cx("flex flex-wrap items-center justify-between gap-2", className)}>
      <div className="min-w-0">
        <p className="text-meta text-warn">{what} alınamadı.</p>
        {/* Dürüstlük: hata, "sorun yok" anlamına GELMEZ. */}
        <p className="text-micro text-muted">Bu, sorun olmadığı anlamına gelmez — durum bilinmiyor.</p>
      </div>
      {onRetry && (
        <Button variant="ghost" size="sm" onClick={onRetry}>
          <RefreshCw size={13} /> Yeniden dene
        </Button>
      )}
    </div>
  );
}
