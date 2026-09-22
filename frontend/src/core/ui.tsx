import type { ClipboardEventHandler, DragEventHandler, KeyboardEventHandler, ReactNode, RefObject } from "react";
import { createContext, forwardRef, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Copy, X } from "lucide-react";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

/* ══════════════════════════════════════════════════════════════════════
   Tema

   Tema data-theme ile <html>'e yazilir; renkleri index.css cozer.
   Bilesenlerin hicbiri temayi bilmez -- sadece semantik sinif kullanir.
   ══════════════════════════════════════════════════════════════════════ */

export type Theme = "light" | "dark" | "system";

const THEME_KEY = "forkos.theme";

/** Isletim sisteminin koyu tercihi; `system` secilince kullanilir. */
const DARK_QUERY = "(prefers-color-scheme: dark)";

function systemTheme(): "light" | "dark" {
  return typeof window !== "undefined" && window.matchMedia?.(DARK_QUERY).matches ? "dark" : "light";
}

export function readTheme(): Theme {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "light" || saved === "dark" || saved === "system") return saved;
  // Varsayilan ACIK. Isletim sisteminin koyu tercihi burayi baglamaz --
  // koyu tema bilincli bir secim (ya da acikca `system` tercihi), kaza degil.
  return "light";
}

/**
 * Tek kaynak. useTheme birden fazla yerde cagrilabilir (ust serit + Ayarlar);
 * hepsi ayni degeri gorur, biri degistirince otekiler aninda gunceller.
 */
const themeListeners = new Set<(theme: Theme) => void>();

/** Bir tercihin ekranda karsiligi: `system` isletim sistemine cozulur. */
function resolvedTheme(theme: Theme): "light" | "dark" {
  return theme === "system" ? systemTheme() : theme;
}

/** `system` tercihinde <html> isletim sistemini izler; tercih degisince
 *  dinleyiciler guncellenir ve data-theme yeniden cozulur. */
function applyResolved(theme: Theme): void {
  document.documentElement.dataset.theme = resolvedTheme(theme);
}

export function applyTheme(theme: Theme): void {
  applyResolved(theme);
  localStorage.setItem(THEME_KEY, theme);
  themeListeners.forEach((notify) => notify(theme));
}

export function useTheme(): [Theme, (next: Theme) => void] {
  const [theme, setLocal] = useState<Theme>(readTheme);
  useEffect(() => {
    themeListeners.add(setLocal);
    return () => {
      themeListeners.delete(setLocal);
    };
  }, []);
  useEffect(() => {
    if (theme !== "system") return;
    const media = window.matchMedia(DARK_QUERY);
    const onChange = () => applyResolved("system");
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [theme]);
  return [theme, applyTheme];
}

/* ══════════════════════════════════════════════════════════════════════
   Yuzeyler
   ══════════════════════════════════════════════════════════════════════ */

/** Sayfalarin ortak genislik ve responsive dis bosluk cercevesi. */
export function PageFrame({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("mx-auto w-full max-w-[1600px] px-4 py-5 sm:px-5 lg:px-6", className)}>{children}</div>;
}

type SectionVariant = "flat" | "card";

/**
 * Icerik bolumu.
 *
 * U1 (Design Foundation v2) sozlesmesi:
 * Varsayilani `flat`: anlamsal gruplama, unboxed, cercevesiz dogal dikey akis.
 * Kutu kabugu yalnizca acikca istendiginde (`variant="card"` veya `flat={false}`)
 * eklenir (`rounded-card border border-subtle bg-surface shadow-card`).
 */
export function Section({
  title,
  hint,
  action,
  children,
  className,
  bodyClassName,
  flat = true,
  variant,
  divider = false,
  titleVariant = "heading",
}: {
  title?: ReactNode;
  hint?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  flat?: boolean;
  variant?: SectionVariant;
  /** Flat modda baslik altina ince ayirac cizgisi ekler. */
  divider?: boolean;
  /** Baslik tipografi tercihi: dogal text-heading (varsayilan) veya label-caps. */
  titleVariant?: "heading" | "caps";
}) {
  const isCard = variant === "card" || (variant === undefined && flat === false);
  const head = title || hint || action;

  return (
    <section className={cx(isCard && "rounded-card border border-subtle bg-surface shadow-card", className)}>
      {head && (
        <header
          className={cx(
            "flex min-h-8 flex-wrap items-center gap-x-3 gap-y-1",
            isCard
              ? "border-b border-subtle px-3.5 py-2"
              : cx("px-0 pb-1.5", divider ? "border-b border-subtle mb-3" : "mb-2"),
          )}
        >
          {title &&
            (typeof title === "string" ? (
              <h2
                className={cx(
                  "shrink-0",
                  titleVariant === "caps" ? "label-caps text-secondary" : "text-heading font-medium text-primary",
                )}
              >
                {title}
              </h2>
            ) : (
              title
            ))}
          <span className="min-w-2 flex-1" />
          {hint && <span className="text-meta text-muted">{hint}</span>}
          {action}
        </header>
      )}
      <div className={cx(isCard && "px-3.5 py-3", bodyClassName)}>{children}</div>
    </section>
  );
}

/** Yalniz gercek gruplama gerektiren form, pane ve katman yuzeyi. */
export function Surface({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("rounded-card border border-subtle bg-surface shadow-card", className)}>{children}</div>;
}

/** Sayisal ozet seridi: hucreleri yatay ayraclarla boler, tek cerceve cizer. */
export function MetricStrip({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cx(
        "grid divide-x divide-subtle overflow-hidden rounded-card border border-subtle bg-surface shadow-card",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function Metric({
  label,
  value,
  hint,
  href,
}: {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  /** Verilirse sayi kutusu o sayfaya giden bir baglantiya donusur. */
  href?: string;
}) {
  const body = (
    <>
      <div className="numeral truncate text-numeral-lg leading-none text-primary transition-colors group-hover:text-accent">
        {value}
      </div>
      <div className="mt-1 truncate text-meta text-secondary transition-colors group-hover:text-accent">{label}</div>
      {hint && <div className="truncate text-meta text-muted">{hint}</div>}
    </>
  );
  const shell = "min-w-0 px-3.5 py-3 sm:px-4";

  return href ? (
    <a href={href} className={cx(shell, "group block")}>
      {body}
    </a>
  ) : (
    <div className={shell}>{body}</div>
  );
}

/** Arama, filtre, siralama ve ana eylemlerin tek responsive seridi. */
export function Toolbar({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cx("flex flex-wrap items-center gap-2 border-y border-subtle py-2.5", className)}>{children}</div>
  );
}

/** Ince ayiracli veri satirlari. Cerceveyi saran kutu (Section) verir. */
export function RowList({
  children,
  className,
  as: Component = "div",
  onKeyDown,
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "ul" | "ol";
  onKeyDown?: React.KeyboardEventHandler<HTMLElement>;
}) {
  return (
    <Component className={cx("divide-y divide-subtle", className)} onKeyDown={onKeyDown}>
      {children}
    </Component>
  );
}

/**
 * Bolum basligi: kucuk kapital etiket + opsiyonel ayirac cizgisi.
 *
 * U1 sozlesmesi: Sayfalar hiyerarsiyi cizgiler yerine bosluk ve tipografi
 * ile kurar; ayirac cizgisi (h-px bg-subtle) varsayilan olarak KAPALIDIR.
 * Cizgi yalnizca acikca `divider` verildiginde cizilir.
 */
export function SectionHeader({
  label,
  hint,
  action,
  divider = false,
}: {
  label: string;
  hint?: ReactNode;
  action?: ReactNode;
  divider?: boolean;
}) {
  return (
    <div className="mb-3 flex items-baseline gap-3">
      <span className="label-caps">{label}</span>
      {divider ? <span className="h-px flex-1 bg-subtle" /> : <span className="flex-1" />}
      {hint && <span className="text-meta text-muted">{hint}</span>}
      {action}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════
   Kontroller

   Yukseklik varsayilani 34px (h-control). Dokunma hedefi gereken yerde
   h-touch (44px) kullan -- ikisi de tailwind.config.js'de tanimli.
   ══════════════════════════════════════════════════════════════════════ */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "warn" | "ok" | "success";

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  primary: "border-primary bg-primary text-canvas hover:opacity-90",
  secondary: "border-strong bg-surface text-primary hover:bg-surface-hover",
  ghost: "border-transparent bg-transparent text-secondary hover:bg-surface-hover hover:text-primary",
  danger: "border-danger-border bg-danger-surface text-danger hover:brightness-95",
  // Durum tonlari: SRS dereceleri gibi "iyiden kotuye" siralanan secimler.
  warn: "border-warn-border bg-warn-surface text-warn hover:brightness-95",
  ok: "border-ok-border bg-ok-surface text-ok hover:brightness-95",
  success: "border-ok bg-ok text-canvas hover:brightness-95",
};

export function Button({
  children,
  onClick,
  variant = "secondary",
  disabled,
  title,
  type = "button",
  size = "md",
  className,
  autoFocus,
  ariaLabel,
  ariaExpanded,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
  title?: string;
  type?: "button" | "submit";
  size?: "sm" | "md";
  className?: string;
  autoFocus?: boolean;
  /** Erisilebilir ad; title verilmezse title kullanilir. */
  ariaLabel?: string;
  /** Acilir paneli tetikleyen dugmeler icin (ekran okuyucu durumu). */
  ariaExpanded?: boolean;
}) {
  return (
    <button
      type={type}
      title={title}
      aria-label={ariaLabel ?? title}
      aria-expanded={ariaExpanded}
      autoFocus={autoFocus}
      disabled={disabled}
      onClick={onClick}
      className={cx(
        "inline-flex shrink-0 items-center justify-center gap-1.5 rounded-control border font-medium transition",
        size === "sm" ? "h-8 px-3 text-meta" : "h-control px-4 text-meta",
        BUTTON_STYLES[variant],
        disabled && "cursor-not-allowed opacity-40 hover:bg-transparent hover:opacity-40",
        className,
      )}
    >
      {children}
    </button>
  );
}

/** Sadece ikon tasiyan buton. title zorunlu -- ekran okuyucu ve tooltip icin. */
export function IconButton({
  children,
  onClick,
  title,
  disabled,
  tone = "neutral",
  ariaPressed,
  ariaExpanded,
  className,
}: {
  children: ReactNode;
  onClick?: () => void;
  title: string;
  disabled?: boolean;
  tone?: "neutral" | "danger";
  /** Aç/kapa düğmeleri için seçili durum (ekran okuyucu sınıfla yetinemez). */
  ariaPressed?: boolean;
  /** Bir panel/popover açan düğmeler için. */
  ariaExpanded?: boolean;
  className?: string;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      aria-pressed={ariaPressed}
      aria-expanded={ariaExpanded}
      disabled={disabled}
      onClick={onClick}
      className={cx(
        "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-control border border-subtle bg-surface transition",
        tone === "danger"
          ? "text-muted hover:border-danger-border hover:bg-danger-surface hover:text-danger"
          : "text-muted hover:bg-surface-hover hover:text-primary",
        disabled && "cursor-not-allowed opacity-40",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function Input({
  value,
  onChange,
  placeholder,
  disabled,
  type = "text",
  className,
  autoFocus,
  onKeyDown,
  onBlur,
  ariaLabel,
  max,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  type?: string;
  className?: string;
  autoFocus?: boolean;
  onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  /** Alandan cikinca kaydeden formlar icin -- ayri bir "kaydet" dugmesi gerekmesin. */
  onBlur?: (value: string) => void;
  ariaLabel?: string;
  max?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      disabled={disabled}
      autoFocus={autoFocus}
      onKeyDown={onKeyDown}
      onBlur={(e) => onBlur?.(e.target.value)}
      aria-label={ariaLabel ?? placeholder}
      max={max}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      className={cx(
        "h-9 rounded-control border border-subtle bg-surface px-3 text-body text-primary",
        "outline-none placeholder:text-muted focus:border-accent focus:ring-1 focus:ring-accent",
        disabled && "cursor-not-allowed opacity-50",
        className,
      )}
    />
  );
}

export function Select({
  value,
  onChange,
  children,
  disabled,
  className,
  ariaLabel,
  id,
}: {
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
  disabled?: boolean;
  className?: string;
  ariaLabel?: string;
  id?: string;
}) {
  return (
    <select
      id={id}
      value={value}
      disabled={disabled}
      aria-label={ariaLabel}
      onChange={(e) => onChange(e.target.value)}
      className={cx(
        "h-9 rounded-control border border-subtle bg-surface px-2.5 text-body text-primary",
        "outline-none focus:border-accent focus:ring-1 focus:ring-accent",
        disabled && "cursor-not-allowed opacity-50",
        className,
      )}
    >
      {children}
    </select>
  );
}

/** Form alani + etiketi. Etiket her zaman gorunur; placeholder etiket degildir. */
export function Field({
  label,
  children,
  hint,
  className,
}: {
  label: string;
  children: ReactNode;
  hint?: ReactNode;
  className?: string;
}) {
  return (
    <label className={cx("block", className)}>
      <span className="mb-1 block text-meta text-secondary">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-meta text-muted">{hint}</span>}
    </label>
  );
}

/** Cok satirli giris. `ref` iletilir ve `onCaret` imlec konumunu bildirir --
 *  otomatik tamamlama gibi imlece bagli davranislar ham <textarea> yazmadan
 *  kurulabilsin diye (kural 15). Iki alan da opsiyoneldir. */
export const Textarea = forwardRef<
  HTMLTextAreaElement,
  {
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    rows?: number;
    className?: string;
    onBlur?: (value: string) => void;
    disabled?: boolean;
    ariaLabel?: string;
    onKeyDown?: KeyboardEventHandler<HTMLTextAreaElement>;
    onPaste?: ClipboardEventHandler<HTMLTextAreaElement>;
    onDrop?: DragEventHandler<HTMLTextAreaElement>;
    onDragOver?: DragEventHandler<HTMLTextAreaElement>;
    /** Imlec konumu degistiginde (tiklama, ok tusu, yazma). */
    onCaret?: (position: number) => void;
  }
>(function Textarea(
  {
    value,
    onChange,
    placeholder,
    rows = 3,
    className,
    onBlur,
    disabled,
    ariaLabel,
    onCaret,
    onKeyDown,
    onPaste,
    onDrop,
    onDragOver,
  },
  ref,
) {
  return (
    <textarea
      ref={ref}
      value={value}
      rows={rows}
      placeholder={placeholder}
      aria-label={ariaLabel ?? placeholder}
      disabled={disabled}
      onKeyDown={onKeyDown}
      onPaste={onPaste}
      onDrop={onDrop}
      onDragOver={onDragOver}
      onBlur={(e) => onBlur?.(e.target.value)}
      onSelect={(e) => onCaret?.(e.currentTarget.selectionStart)}
      onChange={(e) => {
        onChange(e.target.value);
        onCaret?.(e.target.selectionStart);
      }}
      className={cx(
        "w-full resize-y rounded-control border border-subtle bg-surface px-3 py-2 text-body text-primary",
        "outline-none placeholder:text-muted focus:border-accent focus:ring-1 focus:ring-accent",
        disabled && "cursor-not-allowed opacity-50",
        className,
      )}
    />
  );
});

/** Onay kutusu. Ham <input type="checkbox"> yasak — bu primitive kullanilir. */
export function Checkbox({
  checked,
  onChange,
  label,
  disabled,
  className,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: ReactNode;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <label
      className={cx(
        "inline-flex cursor-pointer select-none items-center gap-2 text-meta text-secondary",
        disabled && "cursor-not-allowed opacity-50",
        className,
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded-[3px] border border-strong accent-accent"
      />
      {label}
    </label>
  );
}

/** Kaydirma cubugu (ilerleme gibi aralik girisleri). */
export function Range({
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  disabled,
  ariaLabel,
  ariaValueText,
  className,
}: {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  ariaLabel?: string;
  /** Ekran okuyucuya sayinin anlami: "7 / 10" gibi. */
  ariaValueText?: string;
  className?: string;
}) {
  return (
    <input
      type="range"
      value={value}
      min={min}
      max={max}
      step={step}
      disabled={disabled}
      aria-label={ariaLabel}
      aria-valuetext={ariaValueText}
      onChange={(e) => onChange(Number(e.target.value))}
      className={cx("h-4 w-full cursor-pointer accent-accent", className)}
    />
  );
}

/**
 * Iki uclu aralik secici. Filtrelerde minimum ve maksimum degeri ayni
 * ray uzerinde gosterir; iki tutamac da klavyeyle ayarlanabilir.
 */
export function DualRange({
  minValue,
  maxValue,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  disabled,
  minAriaLabel = "Minimum değer",
  maxAriaLabel = "Maksimum değer",
  className,
}: {
  minValue: number;
  maxValue: number;
  onChange: (minValue: number, maxValue: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  minAriaLabel?: string;
  maxAriaLabel?: string;
  className?: string;
}) {
  const span = Math.max(1, max - min);
  const low = Math.max(min, Math.min(minValue, maxValue));
  const high = Math.min(max, Math.max(maxValue, minValue));
  const left = ((low - min) / span) * 100;
  const width = ((high - low) / span) * 100;
  const dragging = useRef<"min" | "max" | null>(null);

  const valueAt = (clientX: number, element: HTMLDivElement): number => {
    const bounds = element.getBoundingClientRect();
    const ratio = bounds.width > 0 ? Math.max(0, Math.min(1, (clientX - bounds.left) / bounds.width)) : 0;
    const raw = min + ratio * span;
    return Math.max(min, Math.min(max, min + Math.round((raw - min) / step) * step));
  };

  const changeFromPointer = (clientX: number, element: HTMLDivElement, target: "min" | "max") => {
    const next = valueAt(clientX, element);
    if (target === "min") onChange(Math.min(next, high), high);
    else onChange(low, Math.max(next, low));
  };

  return (
    <div
      className={cx(
        "relative h-6 touch-none rounded-full focus-within:ring-2 focus-within:ring-accent",
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
        className,
      )}
      onPointerDown={(event) => {
        if (disabled) return;
        event.preventDefault();
        const next = valueAt(event.clientX, event.currentTarget);
        dragging.current = Math.abs(next - low) <= Math.abs(next - high) ? "min" : "max";
        event.currentTarget.setPointerCapture?.(event.pointerId);
        changeFromPointer(event.clientX, event.currentTarget, dragging.current);
      }}
      onPointerMove={(event) => {
        if (!disabled && dragging.current) changeFromPointer(event.clientX, event.currentTarget, dragging.current);
      }}
      onPointerUp={(event) => {
        dragging.current = null;
        if (event.currentTarget.hasPointerCapture?.(event.pointerId))
          event.currentTarget.releasePointerCapture?.(event.pointerId);
      }}
      onPointerCancel={() => {
        dragging.current = null;
      }}
    >
      <span
        aria-hidden
        className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 overflow-hidden rounded-full bg-surface-sunken"
      >
        <span className="absolute inset-y-0 rounded-full bg-accent" style={{ left: `${left}%`, width: `${width}%` }} />
      </span>
      <span
        aria-hidden
        className="pointer-events-none absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-accent bg-surface"
        style={{ left: `${left}%` }}
      />
      <span
        aria-hidden
        className="pointer-events-none absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-accent bg-surface"
        style={{ left: `${left + width}%` }}
      />
      <input
        type="range"
        value={low}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        aria-label={minAriaLabel}
        onChange={(event) => onChange(Math.min(Number(event.target.value), high), high)}
        className="pointer-events-none absolute inset-0 h-6 w-full opacity-0"
      />
      <input
        type="range"
        value={high}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        aria-label={maxAriaLabel}
        onChange={(event) => onChange(low, Math.max(Number(event.target.value), low))}
        className="pointer-events-none absolute inset-0 h-6 w-full opacity-0"
      />
    </div>
  );
}

/** Sayisal giris; Input'un tipini degil, sayi semantigini tasir. */
export function NumberInput({
  value,
  onChange,
  placeholder,
  disabled,
  className,
  min,
  max,
  step = "any",
  ariaLabel,
}: {
  value: number;
  onChange: (value: number) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  min?: number;
  max?: number;
  step?: number | "any";
  ariaLabel?: string;
}) {
  return (
    <input
      type="number"
      value={Number.isFinite(value) ? String(value) : ""}
      min={min}
      max={max}
      step={step}
      disabled={disabled}
      aria-label={ariaLabel ?? placeholder}
      placeholder={placeholder}
      onChange={(e) => {
        const next = Number(e.target.value);
        if (e.target.value === "" || Number.isFinite(next)) onChange(next);
      }}
      className={cx(
        "h-9 rounded-control border border-subtle bg-surface px-3 text-body text-primary",
        "outline-none placeholder:text-muted focus:border-accent focus:ring-1 focus:ring-accent",
        disabled && "cursor-not-allowed opacity-50",
        className,
      )}
    />
  );
}

/** Gizli dosya secici. Gorumunur tetikleyici (Button) ref ile .click() cagirir.
 *  Ham <input type="file"> yerine bu primitive kullanilir. */
export const FileInput = forwardRef<
  HTMLInputElement,
  {
    accept?: string;
    multiple?: boolean;
    onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
    className?: string;
  }
>(function FileInput({ accept, multiple, onChange, className }, ref) {
  return (
    <input
      ref={ref}
      type="file"
      accept={accept}
      multiple={multiple}
      onChange={onChange}
      className={cx("hidden", className)}
    />
  );
});

/** Düğme üzerindeki "Kopyalandı" geri bildirimi bu süre kalır. */
const COPIED_MS = 1600;

/** Pano erişilemediğinde gösterilen tek cümle: ham istisna metni asla sızmaz. */
const COPIED_WARN = "Pano erişilemedi — tarayıcı izni gerekiyor.";

/**
 * Kopyalama düğmesi. Metni kopyalar, başarıyı hem bildirimle hem de
 * düğmenin kendi üzerinde kısa süreli "Kopyalandı" durumuyla gösterir.
 *
 * Pano API'si yoksa ya da izin reddedilirse İSTİSNA SIZMAZ: ham hata metni
 * kullanıcıya gösterilmez, tek cümlelik uyarı verilir. Bu yüzden her çağıran
 * kendi try/catch'ini yazmak zorunda kalmaz.
 */
export function CopyButton({
  text,
  label = "Kopyala",
  ariaLabel,
  disabled,
  className,
  toastLabel = "Kopyalandı.",
  toastTone = "ok",
}: {
  text: string;
  label?: string;
  ariaLabel?: string;
  disabled?: boolean;
  className?: string;
  /** Basari bildirimi; baglam soyleyebilen cagri yerleri bunu ozelleştirir. */
  toastLabel?: string;
  toastTone?: "ok" | "warn";
}) {
  const toast = useToast();
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const copy = () => {
    if (typeof navigator?.clipboard?.writeText !== "function") {
      toast.push(COPIED_WARN, { tone: "warn" });
      return;
    }
    navigator.clipboard
      .writeText(text)
      .then(() => {
        toast.push(toastLabel, { tone: toastTone });
        setCopied(true);
        window.clearTimeout(timer.current);
        timer.current = window.setTimeout(() => setCopied(false), COPIED_MS);
      })
      .catch(() => toast.push(COPIED_WARN, { tone: "warn" }));
  };

  return (
    <Button
      variant="ghost"
      size="sm"
      disabled={disabled || !text}
      onClick={copy}
      ariaLabel={ariaLabel ?? label}
      className={className}
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
      {copied ? "Kopyalandı" : label}
    </Button>
  );
}

/**
 * Katlanır ayrıntı: kritik durum AÇIK kalır, uzayabilecek ayrıntı katlanır.
 * Ayarlar tanılama yüzeylerinde ve uzun koşu geçmişlerinde ortak desendir
 * (ikinci bir aç/kapa yazılmasın diye burada durur). `aria-expanded` ile
 * ekran okuyucuya durum bildirilir.
 */
export function Disclosure({
  summary,
  children,
  defaultOpen = false,
  className,
}: {
  summary: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={className}>
      <Button variant="ghost" size="sm" ariaExpanded={open} onClick={() => setOpen(!open)}>
        <ChevronDown size={13} className={cx("transition", open && "rotate-180")} />
        {summary}
      </Button>
      {open && <div className="mt-2 space-y-2">{children}</div>}
    </div>
  );
}

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded border border-strong bg-surface px-1.5 py-0.5 font-sans text-micro leading-none text-muted">
      {children}
    </kbd>
  );
}

/* ══════════════════════════════════════════════════════════════════════
   Gosterim
   ══════════════════════════════════════════════════════════════════════ */

/** Durum tonu sözlüğü. `sourceStatus.ts` aynı kümeyi kullanır (tek sözlük). */
export type ChipTone = "neutral" | "accent" | "ok" | "warn" | "danger";
type ChipVariant = "soft" | "outline" | "solid";

/** Semantik ton -> variant basina siniflar. Degerler STATIK dizi:
 *  Tailwind JIT kaynakta tam sinif adini arar, calisma zamani birlestirmez. */
const CHIP_STYLES: Record<ChipVariant, Record<ChipTone, string>> = {
  soft: {
    neutral: "border-subtle bg-surface text-muted",
    accent: "border-accent-border bg-accent-surface text-accent",
    ok: "border-ok-border bg-ok-surface text-ok",
    warn: "border-warn-border bg-warn-surface text-warn",
    danger: "border-danger-border bg-danger-surface text-danger",
  },
  outline: {
    neutral: "border-subtle bg-surface text-secondary",
    accent: "border-accent-border bg-surface text-accent",
    ok: "border-ok-border bg-surface text-ok",
    warn: "border-warn-border bg-surface text-warn",
    danger: "border-danger-border bg-surface text-danger",
  },
  solid: {
    neutral: "border-transparent bg-icon text-canvas",
    accent: "border-accent-border bg-accent text-canvas",
    ok: "border-ok-border bg-ok text-canvas",
    warn: "border-warn-border bg-warn text-canvas",
    danger: "border-danger-border bg-danger text-canvas",
  },
};

/** Kimlik rengi -> siniflar. Sinif adlari TAM LITERAL yazilmali (JIT);
 *  "kind-movie" -> text-[color:var(--kind-movie)] gibi keyfi degerler
 *  kaynakta gorunur oldugu icin derlenir, calisma zamani uretilmez. */
const IDENTITY_STYLES: Record<string, string> = {
  "kind-movie": "text-[color:var(--kind-movie)] border-[color:var(--kind-movie)]",
  "kind-show": "text-[color:var(--kind-show)] border-[color:var(--kind-show)]",
  "kind-anime": "text-[color:var(--kind-anime)] border-[color:var(--kind-anime)]",
  "kind-manga": "text-[color:var(--kind-manga)] border-[color:var(--kind-manga)]",
  "kind-book": "text-[color:var(--kind-book)] border-[color:var(--kind-book)]",
  "kind-audiobook": "text-[color:var(--kind-audiobook)] border-[color:var(--kind-audiobook)]",
  "kind-podcast": "text-[color:var(--kind-podcast)] border-[color:var(--kind-podcast)]",
  "kind-music": "text-[color:var(--kind-music)] border-[color:var(--kind-music)]",
  "kind-game": "text-[color:var(--kind-game)] border-[color:var(--kind-game)]",
  "src-tmdb": "text-[color:var(--src-tmdb)] border-[color:var(--src-tmdb)]",
  "src-anilist": "text-[color:var(--src-anilist)] border-[color:var(--src-anilist)]",
  "src-kitsu": "text-[color:var(--src-kitsu)] border-[color:var(--src-kitsu)]",
  "src-openlibrary": "text-[color:var(--src-openlibrary)] border-[color:var(--src-openlibrary)]",
  "src-itunes": "text-[color:var(--src-itunes)] border-[color:var(--src-itunes)]",
  "src-google-books": "text-[color:var(--src-google-books)] border-[color:var(--src-google-books)]",
  "src-musicbrainz": "text-[color:var(--src-musicbrainz)] border-[color:var(--src-musicbrainz)]",
  "src-igdb": "text-[color:var(--src-igdb)] border-[color:var(--src-igdb)]",
  "src-rawg": "text-[color:var(--src-rawg)] border-[color:var(--src-rawg)]",
  "src-letterboxd": "text-[color:var(--src-letterboxd)] border-[color:var(--src-letterboxd)]",
  "src-imdb": "text-[color:var(--src-imdb)] border-[color:var(--src-imdb)]",
  "src-rottentomatoes": "text-[color:var(--src-rottentomatoes)] border-[color:var(--src-rottentomatoes)]",
  "src-mal": "text-[color:var(--src-mal)] border-[color:var(--src-mal)]",
  "src-goodreads": "text-[color:var(--src-goodreads)] border-[color:var(--src-goodreads)]",
  "src-audible": "text-[color:var(--src-audible)] border-[color:var(--src-audible)]",
  "src-spotify": "text-[color:var(--src-spotify)] border-[color:var(--src-spotify)]",
  "src-rym": "text-[color:var(--src-rym)] border-[color:var(--src-rym)]",
  "src-hltb": "text-[color:var(--src-hltb)] border-[color:var(--src-hltb)]",
  "feed-rss": "text-feed-rss border-[color:var(--feed-rss)]",
  "feed-hn": "text-feed-hn border-[color:var(--feed-hn)]",
  "feed-reddit": "text-feed-reddit border-[color:var(--feed-reddit)]",
  "feed-gh": "text-feed-gh border-[color:var(--feed-gh)]",
};

/** Kimlik rengi siniflari; Chip'in kendisi ve chip gorunumlu butonlar. */
export function identityClasses(id: string): string {
  return IDENTITY_STYLES[id] ?? "text-secondary border-subtle";
}

type ChipBase = {
  children?: ReactNode;
  variant?: ChipVariant;
  icon?: ReactNode;
  size?: "xs" | "sm";
  title?: string;
  "aria-label"?: string;
  className?: string;
};
type ChipProps = ChipBase & ({ tone?: ChipTone; identity?: never } | { identity: string; tone?: never });

/**
 * Tek chip/rozet bileşeni.
 * - `tone`    => semantik anlam (durum, oncelik, saglik).
 * - `identity`=> kimlik rengi ("kind-movie" | "src-tmdb" | "feed-hn").
 * Ikisi ayni anda verilemez (tip duzeyinde engellenir).
 */
export function Chip({
  children,
  variant = "soft",
  tone,
  identity,
  icon,
  size = "sm",
  title,
  "aria-label": ariaLabel,
  className,
}: ChipProps) {
  const style = identity
    ? (IDENTITY_STYLES[identity] ?? "border-subtle bg-surface text-secondary")
    : CHIP_STYLES[variant][tone ?? "neutral"];
  return (
    <span
      title={title}
      aria-label={ariaLabel}
      className={cx(
        "inline-flex shrink-0 items-center gap-1 rounded border font-medium leading-4",
        size === "xs" ? "px-1.5 py-px text-micro" : "px-2 py-0.5 text-micro",
        style,
        className,
      )}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </span>
  );
}

/** Tek secimli filtre cipi. Sayi verilirse saga yazar (sayacsiz da olur). */
export function FilterChip({
  label,
  count,
  active,
  onClick,
  icon,
}: {
  label: string;
  count?: number;
  active: boolean;
  onClick: () => void;
  /** Secim cipleri ikonla taranir (kategori secimi gibi). */
  icon?: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cx(
        "flex h-8 items-center gap-2 rounded-control border px-3 text-meta transition",
        active
          ? "border-accent bg-accent-surface font-medium text-accent"
          : "border-subtle bg-surface text-secondary hover:bg-surface-hover hover:text-primary",
      )}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{label}</span>
      {count !== undefined && (
        <span className={cx("numeral text-meta", active ? "text-accent" : "text-muted")}>{count}</span>
      )}
    </button>
  );
}

/** Tek kutucuk sayisal ozet (saglik paneli gibi ozet satirlari). */
export function MiniStat({ label, value, tone }: { label: string; value: number; tone?: "ok" | "warn" | "danger" }) {
  const color =
    tone === "ok" ? "text-ok" : tone === "warn" ? "text-warn" : tone === "danger" ? "text-danger" : "text-primary";
  return (
    <div className="border-y border-subtle px-3 py-2">
      <div className={cx("numeral text-title leading-tight", color)}>{value}</div>
      <div className="text-meta text-secondary">{label}</div>
    </div>
  );
}

/**
 * Bos durum. Tek gri cumle degil: ne oldugunu soyler, ne yapilacagini gosterir.
 */
export function Empty({
  children,
  title,
  action,
  variant = "inline",
}: {
  children: ReactNode;
  title?: string;
  action?: ReactNode;
  /**
   * "inline"  widget icinde: tek satir, cerceve yok -- kart zaten cerceveli.
   * "page"    bos bir sayfanin ortasi: baslikli, kesikli cerceveli.
   */
  variant?: "inline" | "page";
}) {
  if (variant === "inline" && !title) {
    return <p className="py-5 text-center text-meta text-muted">{children}</p>;
  }
  return (
    <div className="rounded-card border border-dashed border-subtle px-6 py-10 text-center">
      {title && <p className="mb-1.5  text-title text-primary">{title}</p>}
      <p className="mx-auto max-w-md text-body text-secondary">{children}</p>
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

/**
 * Tek basina duran sayisal ozet kutucugu (Today stat'i gibi). Bir serit icinde
 * yan yana sayilar icin MetricStrip + Metric kullan -- Stat kendi cercevesini cizer.
 */
export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-card border border-subtle bg-surface px-4 py-3">
      <div className="numeral text-numeral-xl leading-tight text-primary">{value}</div>
      <div className="text-meta text-secondary">{label}</div>
      {hint && <div className="mt-0.5 text-meta text-muted">{hint}</div>}
    </div>
  );
}

export function Spinner({ label = "Yükleniyor…" }: { label?: string }) {
  return <p className="py-6 text-center text-meta text-muted">{label}</p>;
}

/* ══════════════════════════════════════════════════════════════════════
   Bildirim

   alert() / confirm() yerine. Yazma isleminden sonra geri bildirim burada
   verilir; geri alinabilir islemler action ile gelir.
   ══════════════════════════════════════════════════════════════════════ */

interface Toast {
  id: number;
  message: string;
  tone: "neutral" | "ok" | "warn" | "danger";
  action?: { label: string; run: () => void };
}

interface ToastApi {
  push: (
    message: string,
    /** `durationMs`: geri alma gibi aksiyonlu bildirimler daha uzun kalsin. */
    options?: { tone?: Toast["tone"]; action?: Toast["action"]; durationMs?: number },
  ) => void;
}

type GlobalToastInput = {
  message: string;
  options?: { tone?: Toast["tone"]; action?: Toast["action"]; durationMs?: number };
};

const globalToastListeners = new Set<(toast: GlobalToastInput) => void>();

export function emitGlobalToast(toast: GlobalToastInput): void {
  globalToastListeners.forEach((listener) => listener(toast));
}

export function subscribeGlobalToast(listener: (toast: GlobalToastInput) => void): () => void {
  globalToastListeners.add(listener);
  return () => globalToastListeners.delete(listener);
}

const ToastContext = createContext<ToastApi>({ push: () => {} });

export const useToast = () => useContext(ToastContext);

const TOAST_DOT: Record<Toast["tone"], string> = {
  neutral: "bg-icon",
  ok: "bg-ok",
  warn: "bg-warn",
  danger: "bg-danger",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback<ToastApi["push"]>((message, options) => {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { id, message, tone: options?.tone ?? "neutral", action: options?.action }]);
    window.setTimeout(() => setToasts((current) => current.filter((t) => t.id !== id)), options?.durationMs ?? 6000);
  }, []);

  const api = useMemo(() => ({ push }), [push]);

  useEffect(() => subscribeGlobalToast(({ message, options }) => push(message, options)), [push]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed bottom-5 left-1/2 z-toast flex -translate-x-1/2 flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className="pointer-events-auto flex items-center gap-3 rounded-card border border-subtle bg-surface px-4 py-2.5 text-meta text-primary shadow-overlay"
          >
            <span className={cx("h-1.5 w-1.5 shrink-0 rounded-full", TOAST_DOT[toast.tone])} />
            <span>{toast.message}</span>
            {toast.action && (
              <button
                type="button"
                onClick={() => {
                  toast.action?.run();
                  setToasts((current) => current.filter((t) => t.id !== toast.id));
                }}
                className="ml-1 border-b border-accent-border font-medium text-accent"
              >
                {toast.action.label}
              </button>
            )}
            <button
              type="button"
              aria-label="Kapat"
              title="Kapat"
              onClick={() => setToasts((current) => current.filter((t) => t.id !== toast.id))}
              className="ml-1.5 text-muted transition hover:text-primary"
            >
              <X size={13} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* ══════════════════════════════════════════════════════════════════════
   Bicimleyiciler
   ══════════════════════════════════════════════════════════════════════ */

export function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diff / 60000);
  if (minutes < 1) return "az önce";
  if (minutes < 60) return `${minutes} dk önce`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} sa önce`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} gün önce`;
  return new Date(iso).toLocaleDateString("tr-TR");
}

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/* ── Primitifler (audit: her modul kendi carki yazmasin) ─────────────────── */

/** Tek iskelet blogu (satir/kart). Boyut className ile (h-5, h-20 ...). */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cx("animate-pulse rounded-card bg-surface-sunken", className)} />;
}

/** Liste iskeleti: `rows` adet esit yukseklikte satir. */
export function SkeletonRows({ rows = 5, className }: { rows?: number; className?: string }) {
  return (
    <div aria-hidden className="w-full space-y-2">
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className={cx("h-10", className)} />
      ))}
    </div>
  );
}

/** WAI-ARIA tablist. Sol/sag ok ile gecis; badge sayisi saga yazilir.
 *  Serit dar ekranda YATAY KAYAR: sekmeler sikismaz/kirpilmaz. */
interface TabItem {
  id: string;
  label: string;
  badge?: number;
}

export function Tabs<T extends string>({
  value,
  onChange,
  items,
  ariaLabel,
  panelId,
}: {
  value: T;
  onChange: (next: T) => void;
  items: TabItem[];
  ariaLabel: string;
  /** Sekme -> panel bagi. Verilirse `aria-controls` yazilir. */
  panelId?: (id: string) => string;
}) {
  const listRef = useRef<HTMLDivElement>(null);
  const onKeyDown: KeyboardEventHandler = (event) => {
    const index = items.findIndex((tab) => tab.id === value);
    if (index < 0) return;
    let next = -1;
    if (event.key === "ArrowRight") next = (index + 1) % items.length;
    if (event.key === "ArrowLeft") next = (index - 1 + items.length) % items.length;
    if (next < 0) return;
    event.preventDefault();
    const target = listRef.current?.querySelector<HTMLButtonElement>(`[role="tab"][data-id="${items[next].id}"]`);
    onChange(items[next].id as T);
    target?.focus();
  };
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      ref={listRef}
      onKeyDown={onKeyDown}
      className="flex items-center gap-1 overflow-x-auto"
    >
      {items.map((tab) => {
        const active = tab.id === value;
        // Rozet yalnizca gorsel: ekran okuyucu adi tek parca okunur ("İşler, 12 kayıt").
        const badge = tab.badge !== undefined && tab.badge > 0 ? tab.badge : null;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            data-id={tab.id}
            aria-label={badge === null ? tab.label : `${tab.label}, ${badge} kayıt`}
            aria-selected={active}
            aria-controls={panelId?.(tab.id)}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(tab.id as T)}
            className={cx(
              "flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap border-b-2 px-2.5 text-meta transition",
              active
                ? "border-accent font-medium text-primary"
                : "border-transparent text-muted hover:border-strong hover:text-primary",
            )}
          >
            <span>{tab.label}</span>
            {badge !== null && (
              <span aria-hidden="true" className={cx("tabular-nums", active ? "text-accent" : "text-muted")}>
                {badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/** Capanali acilir panel: disari tik + Escape kapatir, z-popover katmaninda.
 *  `anchorRef` verilirse tetikleyiciye tiklamak kapatmaz (toggle disarida yapilir).
 *
 *  `role="dialog"` verilen kullanimlar Drawer ile ayni odak sozlesmesini alir:
 *  acilista odak panele, Escape ile kapanista odak tetikleyiciye doner ve Tab
 *  panelden kacmaz. `listbox`/`menu` rolleri kendi klavye sozlesmesini tasir;
 *  onlarin odagini biz kapmayiz. */
export function Popover({
  open,
  onClose,
  anchorRef,
  role,
  ariaLabel,
  children,
  className,
}: {
  open: boolean;
  onClose: () => void;
  anchorRef?: { current: HTMLElement | null } | null;
  role?: string;
  ariaLabel?: string;
  children: ReactNode;
  className?: string;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const isDialog = role === "dialog";
  useDialogFocus(open && isDialog, panelRef, onClose);
  useEffect(() => {
    if (!open) return;
    function onDown(event: MouseEvent) {
      const target = event.target as Node;
      const insidePanel = panelRef.current?.contains(target);
      const insideAnchor = anchorRef?.current?.contains(target);
      if (!insidePanel && !insideAnchor) onClose();
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose, anchorRef]);
  if (!open) return null;
  return (
    <div
      ref={panelRef}
      role={role}
      aria-label={ariaLabel}
      tabIndex={isDialog ? -1 : undefined}
      className={cx(
        "absolute z-popover overflow-hidden rounded-overlay border border-strong bg-surface shadow-overlay",
        className,
      )}
    >
      {children}
    </div>
  );
}

/**
 * Modal ve Drawer'in ortak odak yonetimi: ilk odak, Tab dongusu, Escape,
 * kapaninca odagin tetikleyiciye donmesi.
 */
function useDialogFocus(open: boolean, dialogRef: RefObject<HTMLDivElement | null>, onClose: () => void) {
  // Cagiranlar genelde satir ici ok fonksiyonu gecer; onClose kimligi her
  // render'da degisir. Efekt onu ref'ten okur, boylece odak yalnizca panel
  // acilip kapanirken kurulur -- yazarken odak ilk alana geri sicramaz.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  });
  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    const node = dialogRef.current;
    // Odaklanabilir ogeler: gizli/disabled olanlar atlanir (gorunurluk kontrolu
    // jsdom'da guvenilir olmadigi icin yalnizca acik isaretlere bakilir).
    const focusables = () =>
      node
        ? Array.from(
            node.querySelectorAll<HTMLElement>(
              'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
            ),
          ).filter((el) => !el.hasAttribute("hidden"))
        : [];
    // Ilk odak: isaretli alan > govdedeki ilk alan > ilk odaklanabilir oge >
    // diyalogun kendisi. (Basliktaki kapatma dugmesi odagi kapmasin diye
    // govde tercih edilir -- klavye kullanicisi dogrudan icerige girer.)
    const firstField =
      node?.querySelector<HTMLElement>("[data-autofocus]") ??
      node
        ?.querySelector<HTMLElement>("[data-modal-body]")
        ?.querySelector<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ) ??
      focusables()[0] ??
      node;
    firstField?.focus();

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusables();
      if (items.length === 0) {
        event.preventDefault();
        node?.focus();
        return;
      }
      const current = document.activeElement as HTMLElement | null;
      const index = current ? items.indexOf(current) : -1;
      if (event.shiftKey && index <= 0) {
        event.preventDefault();
        items[items.length - 1].focus();
      } else if (!event.shiftKey && (index === -1 || index === items.length - 1)) {
        event.preventDefault();
        items[0].focus();
      }
    };
    // Capture fazinda: icerdeki bir alan Escape'i yutsa bile modal kapanir.
    document.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("keydown", onKey, true);
      // Kapaninca odak tetikleyiciye doner (klavye kullanicisi kaybolmaz).
      opener?.focus?.();
    };
  }, [open, dialogRef]);
}

/**
 * Sagdan acilan calisma paneli (kayit detayi, filtre paneli).
 *
 * Modal ile ayni odak/Escape sozlesmesini paylasir; fark, tam ekran ortada
 * degil kenarda acilmasi ve genislik sinifinin cagirana birakilmasidir.
 */
export function Drawer({
  open,
  onClose,
  title,
  hint,
  children,
  footer,
  ariaLabel,
  className,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  hint?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  ariaLabel?: string;
  className?: string;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  useDialogFocus(open, dialogRef, onClose);
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-drawer flex justify-end bg-[color:var(--overlay-scrim)]"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <aside
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
        aria-label={ariaLabel ?? (typeof title === "string" ? title : undefined)}
        className={cx(
          "flex h-full w-full flex-col border-l border-strong bg-surface shadow-overlay outline-none",
          className ?? "sm:max-w-xl",
        )}
      >
        <header className="flex items-start gap-3 border-b border-subtle px-4 py-3">
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-heading text-primary">{title}</h2>
            {hint && <p className="mt-0.5 text-meta text-muted">{hint}</p>}
          </div>
          <IconButton title="Kapat" onClick={onClose}>
            <X size={15} />
          </IconButton>
        </header>
        <div data-modal-body className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {children}
        </div>
        {footer && <footer className="border-t border-subtle px-4 py-3">{footer}</footer>}
      </aside>
    </div>
  );
}

/**
 * Ortak modal katmani (iOS "sheet" hissi).
 *
 * Neden primitive: ayni desen (sabit katman + scrim + Escape + disari tik)
 * bes ayri dosyada elle tekrarlaniyordu; her kopya kendi kapatma kuralini
 * tasiyor ve biri Escape'i unutunca davranis dosyadan dosyaya degisiyordu.
 * Yeni yuzeyler bunu kullanir.
 *
 * `z-modal` katmani (tailwind zIndex tokeni) modallarin drawer/toast ile
 * dogru siralanmasini garanti eder.
 */
export function Modal({
  open,
  onClose,
  title,
  hint,
  children,
  footer,
  ariaLabel,
  className,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  hint?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  /** Baslik gorsel degilse ekran okuyucu adi. */
  ariaLabel?: string;
  className?: string;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  useDialogFocus(open, dialogRef, onClose);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-modal flex items-end justify-center bg-[color:var(--overlay-scrim)] sm:items-center sm:p-6"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
        aria-label={ariaLabel ?? (typeof title === "string" ? title : undefined)}
        className={cx(
          "max-h-[92vh] w-full overflow-y-auto rounded-t-overlay border border-strong bg-surface shadow-overlay outline-none sm:rounded-overlay",
          className ?? "sm:max-w-md",
        )}
      >
        <header className="flex items-start gap-3 border-b border-subtle px-4 py-3">
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-heading text-primary">{title}</h2>
            {hint && <p className="mt-0.5 text-meta text-muted">{hint}</p>}
          </div>
          <IconButton title="Kapat" onClick={onClose}>
            <X size={15} />
          </IconButton>
        </header>
        <div data-modal-body className="px-4 py-4">
          {children}
        </div>
        {footer && <footer className="border-t border-subtle px-4 py-3">{footer}</footer>}
      </div>
    </div>
  );
}
