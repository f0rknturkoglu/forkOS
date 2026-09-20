import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { BellOff } from "lucide-react";
import { invalidateAfter } from "./invalidation";
import { SNOOZE_PRESETS, snoozeProactivityRun, snoozeUntil } from "./proactivity";
import type { SnoozePreset } from "./proactivity";
import { IconButton, Popover, useToast } from "./ui";

/**
 * H6 erteleme yuzeyi — iki ayri yerde ayni davranis.
 *
 * Onemli kisit: bildirim panelinde menu satirin ICINDE yasayamaz. Bildirim
 * listesi ve panel kutusu tasma (overflow) ile kirpar; satir ici bir menu
 * kirpilir. Bu yuzden menu ICERIGI ayri bir bilesendir ve cagiran onu kendi
 * katmaninda konumlar (Ayarlar satir ici, panel panelin tepesi).
 */

/** On ayar -> mutlak ISO + tazeleme + geri bildirim. Tek yazma yolu. */
export function useRunSnoozeMutation(onSnoozed?: () => void) {
  const toast = useToast();
  return useMutation({
    mutationFn: (input: { runId: number; preset: SnoozePreset }) =>
      snoozeProactivityRun(input.runId, snoozeUntil(input.preset)),
    onSuccess: () => {
      invalidateAfter("settings.write");
      onSnoozed?.();
      toast.push("Erteleme kaydedildi — koşu sessiz kalacak.", { tone: "ok" });
    },
  });
}

/** Menu icerigi: hangi kosu erteleniyor + on ayarlar. */
export function SnoozePresetList({
  headline,
  pending,
  onPick,
}: {
  headline: string;
  pending: boolean;
  onPick: (preset: SnoozePreset) => void;
}) {
  return (
    <>
      <p className="truncate border-b border-subtle px-2.5 pb-1.5 pt-0.5 text-micro text-muted">{headline}</p>
      {SNOOZE_PRESETS.map((preset) => (
        <button
          key={preset.id}
          type="button"
          role="menuitem"
          disabled={pending}
          onClick={() => onPick(preset.id)}
          className="block w-full px-2.5 py-1.5 text-left text-meta text-secondary transition hover:bg-surface-hover hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
        >
          {preset.label}
        </button>
      ))}
    </>
  );
}

/** Hazir satir ici kontrol: tetikleyici + kendi menusu (Ayarlar kosu listesi). */
export function ProactivitySnoozeButton({
  runId,
  title,
  headline,
}: {
  runId: number;
  /** Tetikleyicinin erisilebilir adi. */
  title: string;
  /** Menunun basligi: hangi kosu erteleniyor. */
  headline: string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const snooze = useRunSnoozeMutation(() => setOpen(false));

  return (
    <div ref={rootRef} className="relative">
      <IconButton
        title={title}
        ariaExpanded={open}
        disabled={snooze.isPending}
        onClick={() => setOpen((current) => !current)}
      >
        <BellOff size={14} />
      </IconButton>
      <Popover
        open={open}
        onClose={() => setOpen(false)}
        anchorRef={rootRef}
        role="menu"
        ariaLabel={title}
        className="right-0 top-9 w-44 py-1"
      >
        <SnoozePresetList
          headline={headline}
          pending={snooze.isPending}
          onPick={(preset) => snooze.mutate({ runId, preset })}
        />
      </Popover>
    </div>
  );
}
