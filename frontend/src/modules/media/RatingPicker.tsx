import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Eraser, Star } from "lucide-react";

import { api } from "@/core/api";
import type { MediaItem } from "@/core/types";
import { Button, Range } from "@/core/ui";

/** Puanlanmamis kayitta ray bu degerde durur; deger gostergesi "Puanlanmadı" der. */
const UNSET_SLIDER_VALUE = 5;

/**
 * Tek puanlama kontrolu: 1-10 arasi bir kaydirma cubugu (Faz 5).
 *
 * Yildiz dizisi + cip kombinasyonu bilincli olarak YOK: klavye ile
 * erisilebilir tek kontrol, ekran okuyucuya `{n} / 10` okur. Kaydetme
 * `PATCH /media/{id} {score}`; temizleme `score: null` gonderir.
 */
export function RatingPicker({ item, online }: { item: MediaItem; online: boolean }) {
  const [score, setScore] = useState<number | null>(item.score ?? null);
  const mutation = useMutation({
    mutationFn: (next: number | null) => api.patch(`/media/${encodeURIComponent(item.id)}`, { score: next }),
    onSuccess: (_result, next) => {
      setScore(next);
      invalidateAfter("media.write");
    },
  });

  // Sunucu degeri degistiginde (tazeleme, baska yuzeydeki duzenleme) ray esitlenir.
  useEffect(() => {
    setScore(item.score ?? null);
  }, [item.score]);

  const disabled = !online || mutation.isPending;
  const shown = score ?? UNSET_SLIDER_VALUE;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-3">
        <Range
          value={shown}
          onChange={setScore}
          min={1}
          max={10}
          step={1}
          disabled={disabled}
          ariaLabel="Puan"
          ariaValueText={`${shown} / 10`}
          className="max-w-xs"
        />
        <span className="numeral inline-flex items-center gap-1.5 text-body text-primary">
          <Star size={14} aria-hidden="true" className="text-muted" />
          {score == null ? "Puanlanmadı" : `${score} / 10`}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="primary"
          disabled={disabled || score == null || score === item.score}
          onClick={() => mutation.mutate(score)}
        >
          Puanı kaydet
        </Button>
        {item.score != null && (
          <Button size="sm" disabled={disabled} onClick={() => mutation.mutate(null)}>
            <Eraser size={13} aria-hidden="true" /> Puanı temizle
          </Button>
        )}
      </div>
      {mutation.error && (
        <p role="alert" className="text-meta text-danger">
          Puan kaydedilemedi: {mutation.error.message}
        </p>
      )}
    </div>
  );
}
