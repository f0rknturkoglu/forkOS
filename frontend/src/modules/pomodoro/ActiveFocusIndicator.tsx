import { Pause, Timer } from "lucide-react";
import { cx } from "@/core/ui";
import { openPomodoro } from "./dock";
import { useActivePomodoro, usePomodoroClock } from "./queries";
import { clock, remaining } from "./time";

/**
 * Kabuk basligindaki aktif odak gostergesi.
 *
 * Neden baslikta: seans sayfa degistirince kaybolmuyordu -- kullanici baska bir
 * moduldeyken odagin surdugunu (ve ne kadar kaldigini) goremiyordu. Hizli eylem
 * dock'u sag altta duruyor ama goz orada degil.
 *
 * Oturum YOKKEN hicbir sey cizilmez: basligi bos bir yer tutucuyla doldurmak
 * seridin hizasini bozar ve kullaniciya bilgi vermez. Tiklayinca global odak
 * paneli acilir (duraklat/tamamla/tam ekran orada).
 */
export function ActiveFocusIndicator() {
  const { data: active = null } = useActivePomodoro();
  const now = usePomodoroClock(active);

  if (!active) return null;

  const left = remaining(active, now);
  const paused = Boolean(active.paused_at);
  const label = active.topic || active.context_title || "Bağımsız odak";

  return (
    <button
      type="button"
      onClick={() => openPomodoro()}
      title={`${label} · ${paused ? "duraklatıldı" : "çalışıyor"} — odak kontrollerini aç`}
      aria-label={`Aktif odak: ${label}, ${clock(left)}, ${paused ? "duraklatıldı" : "çalışıyor"}`}
      className={cx(
        // Seritteki diger kontrollerle ayni taban cizgisi: h-8, rounded-control.
        "flex h-8 max-w-48 shrink-0 items-center gap-1.5 rounded-control border px-2 transition",
        paused
          ? "border-subtle bg-surface text-muted hover:bg-surface-hover hover:text-primary"
          : "border-accent-border bg-accent-surface text-accent hover:brightness-95",
      )}
    >
      {paused ? <Pause size={13} /> : <Timer size={13} />}
      <span className="numeral text-meta tabular-nums">{clock(left)}</span>
      <span className="hidden truncate text-meta md:inline">{label}</span>
      {!paused && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-ok" aria-hidden />}
    </button>
  );
}

ActiveFocusIndicator.displayName = "ActiveFocusIndicator";
