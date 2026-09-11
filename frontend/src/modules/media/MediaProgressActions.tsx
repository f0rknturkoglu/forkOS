import { invalidateAfter } from "@/core/invalidation";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Check, ChevronRight, RotateCcw, SlidersHorizontal } from "lucide-react";
import { api } from "@/core/api";
import type { MediaItem } from "@/core/types";
import type { components } from "@/generated/api-schema";
import { Button, Field, NumberInput, cx, useToast } from "@/core/ui";

type MediaConsumptionIn = components["schemas"]["MediaConsumptionIn"];
type ConsumptionAction = "quick" | "set" | "finish";

/** Geri al penceresi: toast bu sure boyunca aksiyonu tasir. */
const UNDO_WINDOW_MS = 8000;

const MEASURE_LABELS: Record<string, string> = {
  chapter: "bölüm",
  episode: "bölüm",
  hour: "saat",
  item: "kayıt",
  minute: "dakika",
  page: "sayfa",
  percent: "%",
  track: "parça",
};

export function measureLabel(measure: string | null | undefined): string {
  return MEASURE_LABELS[measure ?? "item"] ?? measure ?? "kayıt";
}

/** `media_consumption.action` -> kullanici dili (gecmis satirlari). */
const ACTION_LABELS: Record<string, string> = {
  complete_unit: "Bölüm tamamlandı",
  finish: "Tamamlama",
  quick: "Hızlı ilerleme",
  session: "Seans",
  set: "Düzeltme",
  uncomplete_unit: "Geri alındı",
};

export function actionLabel(action: string | null | undefined): string {
  if (!action) return "Kayıt";
  return ACTION_LABELS[action] ?? action;
}

/**
 * Tur duyarli eylem dili (Faz 5).
 *
 * Kitapta "Oku", dizide "İzle": ayni uc nokta farkli turler icin farkli
 * konusur. Fiil cekimleri hazir tutulur cunku Turkce'de ek uyumu (İzle-meye /
 * Oku-maya / Oyna-maya) kural ile degil sozlukle dogrudur.
 */
interface KindLanguage {
  verb: string;
  start: string;
  resume: string;
  finish: string;
  restart: string;
  session: string;
}

const KIND_LANGUAGES: Record<string, KindLanguage> = {
  movie: {
    verb: "İzle",
    start: "İzlemeye başla",
    resume: "İzlemeye devam et",
    finish: "İzlemeyi tamamla",
    restart: "Sıfırdan başla",
    session: "İzleme seansı başlat",
  },
  show: {
    verb: "İzle",
    start: "İzlemeye başla",
    resume: "İzlemeye devam et",
    finish: "İzlemeyi tamamla",
    restart: "Sıfırdan başla",
    session: "İzleme seansı başlat",
  },
  anime: {
    verb: "İzle",
    start: "İzlemeye başla",
    resume: "İzlemeye devam et",
    finish: "İzlemeyi tamamla",
    restart: "Sıfırdan başla",
    session: "İzleme seansı başlat",
  },
  book: {
    verb: "Oku",
    start: "Okumaya başla",
    resume: "Okumaya devam et",
    finish: "Okumayı tamamla",
    restart: "Sıfırdan başla",
    session: "Okuma seansı başlat",
  },
  manga: {
    verb: "Oku",
    start: "Okumaya başla",
    resume: "Okumaya devam et",
    finish: "Okumayı tamamla",
    restart: "Sıfırdan başla",
    session: "Okuma seansı başlat",
  },
  audiobook: {
    verb: "Dinle",
    start: "Dinlemeye başla",
    resume: "Dinlemeye devam et",
    finish: "Dinlemeyi tamamla",
    restart: "Sıfırdan başla",
    session: "Dinleme seansı başlat",
  },
  podcast: {
    verb: "Dinle",
    start: "Dinlemeye başla",
    resume: "Dinlemeye devam et",
    finish: "Dinlemeyi tamamla",
    restart: "Sıfırdan başla",
    session: "Dinleme seansı başlat",
  },
  music: {
    verb: "Dinle",
    start: "Dinlemeye başla",
    resume: "Dinlemeye devam et",
    finish: "Dinlemeyi tamamla",
    restart: "Sıfırdan başla",
    session: "Dinleme seansı başlat",
  },
  game: {
    verb: "Oyna",
    start: "Oynamaya başla",
    resume: "Oynamaya devam et",
    finish: "Oyunu tamamla",
    restart: "Sıfırdan başla",
    session: "Oyun seansı başlat",
  },
};

/** Legacy/bilinmeyen tur (ör. provider'siz eski satirlar): notr ama tutarli dil. */
const FALLBACK_LANGUAGE: KindLanguage = {
  verb: "İncele",
  start: "İncelemeye başla",
  resume: "İncelemeye devam et",
  finish: "Tamamla",
  restart: "Sıfırdan başla",
  session: "İnceleme seansı başlat",
};

export function kindLanguage(kind: string | null | undefined): KindLanguage {
  return (kind && KIND_LANGUAGES[kind]) || FALLBACK_LANGUAGE;
}

/** Her çağrı kendi idempotency anahtarını üretir; gövde tekrar kullanılmaz. */
export function consumptionBody(
  action: ConsumptionAction,
  item: Pick<MediaItem, "progress_measure">,
  value?: number,
): MediaConsumptionIn {
  const measure = item.progress_measure ?? "item";
  const base = { action, client_uuid: crypto.randomUUID(), measure };
  if (action === "quick") return { ...base, amount: 1 };
  if (action === "set") return { ...base, progress_after: value };
  return base;
}

export function MediaProgressActions({
  item,
  online,
  compact = false,
  onChanged,
}: {
  item: MediaItem;
  online: boolean;
  compact?: boolean;
  onChanged: () => void;
}) {
  const toast = useToast();
  const [setting, setSetting] = useState(false);
  const [value, setValue] = useState(item.progress ?? 0);
  const language = kindLanguage(item.kind);
  const measure = item.progress_measure ?? "item";

  /**
   * Geri alma yeni ve tutarli bir tuketim yazar; gecmis append-only oldugu icin
   * onceki event guncellenmez (action="set", note="geri alındı").
   */
  const undo = (previous: number) => {
    void api
      .post(`/media/${encodeURIComponent(item.id)}/consumptions`, {
        action: "set",
        client_uuid: crypto.randomUUID(),
        measure,
        note: "geri alındı",
        progress_after: previous,
      })
      .then(() => {
        invalidateAfter("media.write");
        onChanged();
        toast.push("İlerleme geri alındı.", { tone: "ok" });
      })
      .catch((error: Error) => toast.push(error.message, { tone: "danger" }));
  };

  const mutation = useMutation({
    mutationFn: ({ action, value: next }: { action: ConsumptionAction; value?: number; previous: number }) =>
      api.post(`/media/${encodeURIComponent(item.id)}/consumptions`, consumptionBody(action, item, next)),
    onSuccess: (_result, variables) => {
      invalidateAfter("media.write");
      onChanged();
      toast.push(`${actionLabel(variables.action)} kaydedildi.`, {
        tone: "ok",
        durationMs: UNDO_WINDOW_MS,
        action: { label: "Geri al", run: () => undo(variables.previous) },
      });
    },
    onError: (error: Error) => {
      // Iyimser yazim yok: tek geri alma katmani sorgu tazelemesidir.
      invalidateAfter("media.write");
      toast.push(error.message, { tone: "danger" });
    },
  });
  const cycle = useMutation({
    mutationFn: () => api.post(`/media/${encodeURIComponent(item.id)}/cycles`, {}),
    onSuccess: () => {
      invalidateAfter("media.write");
      onChanged();
    },
  });

  if (item.status === "completed" || item.status === "dropped") {
    return (
      <div className={cx("flex min-w-0 flex-wrap items-center gap-2", compact && "gap-1.5")}>
        <Button size="sm" variant="primary" disabled={!online || cycle.isPending} onClick={() => cycle.mutate()}>
          <RotateCcw size={14} aria-hidden="true" /> {language.restart}
        </Button>
        {cycle.error && (
          <p role="alert" className="basis-full text-meta text-danger">
            Yeni tur başlatılamadı: {cycle.error.message}
          </p>
        )}
      </div>
    );
  }

  const disabled = !online || mutation.isPending;
  const previous = item.progress ?? 0;

  return (
    <div className="min-w-0 space-y-3">
      <div className="min-w-0">
        <p className="label-caps">İlerleme kaydet</p>
        <div
          role="group"
          aria-label="İlerleme kaydet"
          className={cx("mt-1.5 flex min-w-0 flex-wrap items-center gap-2", compact && "gap-1.5")}
        >
          <Button size="sm" disabled={disabled} onClick={() => mutation.mutate({ action: "quick", previous })}>
            <ChevronRight size={14} aria-hidden="true" /> +1 {measureLabel(measure)}
          </Button>
          <Button
            size="sm"
            variant="primary"
            disabled={disabled}
            onClick={() => mutation.mutate({ action: "finish", previous })}
          >
            <Check size={14} aria-hidden="true" /> {language.finish}
          </Button>
        </div>
      </div>

      <div className="min-w-0 border-t border-subtle pt-3">
        <p className="label-caps">İlerlemeyi düzelt</p>
        <div
          role="group"
          aria-label="İlerlemeyi düzelt"
          className={cx("mt-1.5 flex min-w-0 flex-wrap items-center gap-2", compact && "gap-1.5")}
        >
          <Button size="sm" disabled={disabled} onClick={() => setSetting((open) => !open)}>
            <SlidersHorizontal size={13} aria-hidden="true" /> {setting ? "Vazgeç" : "İlerlemeyi ayarla"}
          </Button>
          {setting && (
            <form
              aria-label="Kesin ilerleme"
              className="grid min-w-0 basis-full grid-cols-[minmax(0,1fr)_auto] items-end gap-2 pt-1 sm:grid-cols-[minmax(0,8rem)_auto_auto]"
              onSubmit={(event) => {
                event.preventDefault();
                const progress = Number(value);
                if (!Number.isFinite(progress) || progress < 0) return;
                mutation.mutate({ action: "set", value: progress, previous });
              }}
            >
              <Field label="İlerleme değeri" className="min-w-0">
                <NumberInput
                  value={value}
                  onChange={setValue}
                  min={0}
                  step="any"
                  disabled={disabled}
                  className="w-full min-w-0"
                />
              </Field>
              <span className="pb-2 text-meta text-muted">{measureLabel(measure)}</span>
              <Button type="submit" size="sm" disabled={disabled} className="col-span-2 w-full sm:col-span-1 sm:w-auto">
                İlerlemeyi kaydet
              </Button>
            </form>
          )}
        </div>
      </div>

      {mutation.error && (
        <p role="alert" className="text-meta text-danger">
          İlerleme kaydedilemedi: {mutation.error.message}
        </p>
      )}
    </div>
  );
}
