/**
 * Kayıtlı görünümlerin PAYLAŞILAN okuma yolu.
 *
 * Kaydetme/silme/sabitleme arayüzü `SavedViewPicker` içindedir; burada üç
 * şey tek yerde durur ki sayfalar kendi sorgularını yazmasın:
 *
 *   useSavedViews(module)        modülün görünümleri (picker ile AYNI anahtar)
 *   usePinnedSavedViews()        sidebar'ın sabitlenmiş listesi
 *   useAppliedSavedView(...)     `?saved=<id>` derin bağlantısını uygular
 *
 * Derin bağlantı sözleşmesi: `#/<rota>?saved=<gorunum-id>`. Bilinmeyen/eski bir
 * id sessizce yok sayılır -- filtre anahtarlarını yalnız sayfa bilir
 * (`apply`), tanımadığı anahtarı zaten uygulamaz.
 */
import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type { SavedViewRow } from "./SavedViewPicker";

/** Sayfa sorgu anahtarı; `SavedViewPicker` ile aynı olmalı (tek istek). */
export const savedViewsKey = (module: string) => ["views", module] as const;
/** Sidebar anahtarı: tüm modüllerin sabitlenmiş görünümleri. */
export const PINNED_VIEWS_KEY = ["views", "pinned"] as const;

/** Modülün kayıtlı görünümleri (picker ile paylaşılan anahtar). */
export function useSavedViews(module: string) {
  return useQuery({
    queryKey: savedViewsKey(module),
    queryFn: () => api.get<SavedViewRow[]>(`/views?module=${encodeURIComponent(module)}`),
  });
}

/** Sidebar: yalnız sabitlenenler, sunucu sırasıyla (pinned → position → id). */
export function usePinnedSavedViews() {
  return useQuery({
    queryKey: PINNED_VIEWS_KEY,
    queryFn: () => api.get<SavedViewRow[]>("/views").then((rows) => rows.filter((row) => row.pinned)),
  });
}

/**
 * `?saved=<id>` verilmişse görünümün filtresini BİR KEZ uygular. Görünüm
 * bulunamazsa (yüklenmedi, silinmiş, başka modüle ait) hiçbir şey yapmaz.
 */
export function useAppliedSavedView(
  module: string,
  params: URLSearchParams,
  apply: (filter: Record<string, unknown>) => void,
): void {
  const requestedId = params.get("saved");
  const { data = [] } = useSavedViews(module);
  const appliedRef = useRef<string | null>(null);

  useEffect(() => {
    if (!requestedId) {
      appliedRef.current = null;
      return;
    }
    if (appliedRef.current === requestedId) return;
    const view = data.find((row) => row.id === requestedId);
    if (!view) return;
    appliedRef.current = requestedId;
    apply(view.filter ?? {});
  }, [requestedId, data, apply]);
}
