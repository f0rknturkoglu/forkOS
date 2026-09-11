/**
 * Kompakt skor aralığı kontrolü.
 *
 * Önceden skor slider'ı sonuçların üstünde geniş bir kart kaplayıp listeyi
 * ekranın altına itiyordu. Artık varsayılan durumda yalnızca tek satırlık bir
 * tetikleyici var; ray ve hazır aralıklar küçük bir popover'da açılıyor.
 *
 * Sözleşme:
 *  - `-1` kullanıcıya "Elendi" olarak görünür (kayıt silinmez, elenmiş sayılır).
 *  - Tutamaçlar sürüklenirken API'ye sorgu gitmez; bırakınca/kısa debounce
 *    sonunda TEK commit yapılır.
 *  - İki tutamaç da klavyeyle (ok tuşları) ayarlanabilir ve ayrı aria etiketi taşır.
 *  - Hazır aralıklar ÖRTÜŞMEZ: 80–100 · 70–79 · 40–69 · 0–39 · Elendi.
 */

import { useEffect, useRef, useState } from "react";
import { ChevronDown, RotateCcw, SlidersHorizontal } from "lucide-react";
import { Button, DualRange, FilterChip, Popover, cx } from "@/core/ui";
import { SCORE_PRESETS, scoreRangeLabel } from "./filterState";

interface Props {
  min: number | undefined;
  max: number | undefined;
  onChange: (min: number | undefined, max: number | undefined) => void;
  disabled?: boolean;
}

const SLIDER_MIN = -1;
const SLIDER_MAX = 100;

/** Skoru kullanıcı diline çevirir; -1 tek başına "Elendi" demektir. */
function handleLabel(value: number, role: "min" | "max"): string {
  if (value === -1) return "Elendi";
  return role === "min" ? `En az ${value}` : `En çok ${value}`;
}

export function ScoreRangeControl({ min, max, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [dragging, setDragging] = useState(false);
  const anchorRef = useRef<HTMLButtonElement>(null);
  const committedMin = min ?? SLIDER_MIN;
  const committedMax = max ?? SLIDER_MAX;
  const [draft, setDraft] = useState<[number, number]>([committedMin, committedMax]);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  // Dışarıdan gelen değer değişince (preset, kayıtlı görünüm, chip temizleme)
  // taslağı senkronize et — ama kullanıcı sürüklerken değil.
  useEffect(() => {
    if (!dragging) setDraft([min ?? SLIDER_MIN, max ?? SLIDER_MAX]);
  }, [min, max, dragging]);

  /** Taslağı tek seferde commit eder; değişiklik yoksa çağırmaz. */
  const commit = () => {
    if (draft[0] === committedMin && draft[1] === committedMax) return;
    if (draft[0] === SLIDER_MIN && draft[1] === SLIDER_MAX) onChangeRef.current(undefined, undefined);
    else onChangeRef.current(draft[0], draft[1]);
  };
  const commitRef = useRef(commit);
  commitRef.current = commit;

  // Klavye ile değişiklikte (pointer bırakma yok) kısa debounce ile commit et.
  useEffect(() => {
    if (dragging) return;
    if (draft[0] === committedMin && draft[1] === committedMax) return;
    const timer = window.setTimeout(() => commitRef.current(), 250);
    return () => window.clearTimeout(timer);
  }, [draft, dragging, committedMin, committedMax]);

  const active = min !== undefined || max !== undefined;

  return (
    <span className="relative inline-flex" ref={anchorRef}>
      <Button
        size="sm"
        variant={active ? "secondary" : "ghost"}
        disabled={disabled}
        ariaLabel={`Skor aralığı: ${scoreRangeLabel(min, max)}`}
        ariaExpanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <SlidersHorizontal size={12} />
        <span className="tabular-nums">Skor: {scoreRangeLabel(min, max)}</span>
        <ChevronDown size={12} className={cx("transition", open && "rotate-180")} />
      </Button>
      <Popover
        open={open}
        onClose={() => setOpen(false)}
        anchorRef={anchorRef}
        role="dialog"
        ariaLabel="Skor aralığı"
        className="left-0 top-[calc(100%+0.375rem)] w-[min(22rem,calc(100vw-2rem))] p-3"
      >
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-1.5">
            {SCORE_PRESETS.map((preset) => {
              const presetActive = min === preset.min && max === preset.max;
              return (
                <FilterChip
                  key={preset.label}
                  label={preset.label}
                  active={presetActive}
                  onClick={() => {
                    setDraft([preset.min ?? SLIDER_MIN, preset.max ?? SLIDER_MAX]);
                    onChange(preset.min, preset.max);
                  }}
                />
              );
            })}
          </div>

          <div
            className="rounded-control border border-subtle bg-surface-sunken/40 px-3 py-2.5"
            onPointerDown={() => setDragging(true)}
            onPointerUp={() => {
              setDragging(false);
              commitRef.current();
            }}
            onPointerCancel={() => {
              setDragging(false);
              commitRef.current();
            }}
            onPointerLeave={() => setDragging(false)}
            onBlur={() => commitRef.current()}
          >
            <div className="mb-2 flex items-center justify-between text-meta">
              <span className="rounded-control bg-surface px-2 py-0.5 tabular-nums text-primary">
                {handleLabel(draft[0], "min")}
              </span>
              <span className="rounded-control bg-surface px-2 py-0.5 tabular-nums text-primary">
                {handleLabel(draft[1], "max")}
              </span>
            </div>
            <DualRange
              min={SLIDER_MIN}
              max={SLIDER_MAX}
              step={1}
              minValue={draft[0]}
              maxValue={draft[1]}
              minAriaLabel="Minimum skor (Elendi = -1)"
              maxAriaLabel="Maksimum skor"
              onChange={(nextMin, nextMax) => setDraft([nextMin, nextMax])}
            />
            <div className="mt-1 flex justify-between text-micro text-muted" aria-hidden>
              <span>Elendi</span>
              <span>0</span>
              <span>40</span>
              <span>70</span>
              <span>100</span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-meta text-muted">{scoreRangeLabel(min, max)} · Elendi = -1 puan</span>
            <Button
              size="sm"
              variant="ghost"
              disabled={!active}
              onClick={() => {
                setDraft([SLIDER_MIN, SLIDER_MAX]);
                onChange(undefined, undefined);
              }}
            >
              <RotateCcw size={12} /> Sıfırla
            </Button>
          </div>
        </div>
      </Popover>
    </span>
  );
}
