import { invalidateAfter } from "@/core/invalidation";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Check, ChevronRight, RotateCcw, SlidersHorizontal } from "lucide-react";
import { api } from "@/core/api";
import type { MediaItem } from "@/core/types";
import type { components } from "@/generated/api-schema";
import { Button, Field, NumberInput, cx } from "@/core/ui";
import {} from "@/lib/hooks";

export type MediaConsumptionIn = components["schemas"]["MediaConsumptionIn"];
type ConsumptionAction = "quick" | "set" | "finish";


const MEASURE_LABELS: Record<string, string> = {
  chapter: "bölüm",
  episode: "bölüm",
  hour: "saat",
  item: "öğe",
  minute: "dakika",
  page: "sayfa",
  percent: "%",
  track: "parça",
};

export function measureLabel(measure: string | null | undefined): string {
  return MEASURE_LABELS[measure ?? "item"] ?? measure ?? "öğe";
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

function quickLabel(measure: string | null | undefined): string {
  if (measure === "episode" || measure === "chapter") return "Sonraki bölüm";
  if (measure === "page") return "Bir sayfa ilerle";
  if (measure === "minute") return "Bir dakika ilerle";
  if (measure === "track") return "Sonraki parça";
  return "Bir artır";
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
  const [setting, setSetting] = useState(false);
  const [value, setValue] = useState(item.progress ?? 0);
  const mutation = useMutation({
    mutationFn: ({ action, value: next }: { action: ConsumptionAction; value?: number }) =>
      api.post(`/media/${encodeURIComponent(item.id)}/consumptions`, consumptionBody(action, item, next)),
    onSuccess: () => {
      invalidateAfter("media.write");
      onChanged();
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
        <Button
          size="sm"
          variant="primary"
          disabled={!online || cycle.isPending}
          onClick={() => cycle.mutate()}
        >
          <RotateCcw size={14} aria-hidden="true" /> Yeni tur başlat
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

  return (
    <div className={cx("flex min-w-0 flex-wrap items-center gap-2", compact && "gap-1.5")}>
      <Button
        size="sm"
        disabled={disabled}
        onClick={() => mutation.mutate({ action: "quick" })}
      >
        <ChevronRight size={14} aria-hidden="true" /> {quickLabel(item.progress_measure)}
      </Button>
      <Button
        size="sm"
        disabled={disabled}
        onClick={() => setSetting((open) => !open)}
      >
        <SlidersHorizontal size={13} aria-hidden="true" /> {setting ? "Vazgeç" : "İlerlemeyi ayarla"}
      </Button>
      <Button
        size="sm"
        variant="primary"
        disabled={disabled}
        onClick={() => mutation.mutate({ action: "finish" })}
      >
        <Check size={14} aria-hidden="true" /> Tamamlandı olarak işaretle
      </Button>
      {setting && (
        <form
          aria-label="Kesin ilerleme"
          className="grid min-w-0 basis-full grid-cols-[minmax(0,1fr)_auto] items-end gap-2 pt-1 sm:grid-cols-[minmax(0,8rem)_auto_auto]"
          onSubmit={(event) => {
            event.preventDefault();
            const progress = Number(value);
            if (!Number.isFinite(progress) || progress < 0) return;
            mutation.mutate({ action: "set", value: progress });
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
          <span className="pb-2 text-meta text-muted">{measureLabel(item.progress_measure)}</span>
          <Button type="submit" size="sm" disabled={disabled} className="col-span-2 w-full sm:col-span-1 sm:w-auto">İlerlemeyi kaydet</Button>
        </form>
      )}
      {mutation.error && (
        <p role="alert" className="basis-full text-meta text-danger">
          İlerleme kaydedilemedi: {mutation.error.message}
        </p>
      )}
    </div>
  );
}
