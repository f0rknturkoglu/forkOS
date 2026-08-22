import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

/* ══════════════════════════════════════════════════════════════════════
   Tema

   Tema data-theme ile <html>'e yazilir; renkleri index.css cozer.
   Bilesenlerin hicbiri temayi bilmez -- sadece semantik sinif kullanir.
   ══════════════════════════════════════════════════════════════════════ */

export type Theme = "light" | "dark";

const THEME_KEY = "forkos.theme";

export function readTheme(): Theme {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "light" || saved === "dark") return saved;
  // Varsayilan ACIK. Isletim sisteminin koyu tercihi burayi baglamaz --
  // koyu tema bilincli bir secim, kaza degil.
  return "light";
}

/**
 * Tek kaynak. useTheme birden fazla yerde cagrilabilir (ust serit + Ayarlar);
 * hepsi ayni degeri gorur, biri degistirince otekiler aninda gunceller.
 */
const themeListeners = new Set<(theme: Theme) => void>();

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_KEY, theme);
  themeListeners.forEach((notify) => notify(theme));
}

export function useTheme(): [Theme, (next: Theme) => void] {
  const [theme, setLocal] = useState<Theme>(readTheme);
  useEffect(() => {
    themeListeners.add(setLocal);
    return () => { themeListeners.delete(setLocal); };
  }, []);
  return [theme, applyTheme];
}

/* ══════════════════════════════════════════════════════════════════════
   Yuzeyler
   ══════════════════════════════════════════════════════════════════════ */

/** Kutu. Derinlik 1px kenarlik + cok hafif kabartmayla kurulur, agir golgeyle degil. */
export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cx("rounded-card border border-subtle bg-surface shadow-card", className)}>
      {children}
    </div>
  );
}

export function Panel({
  title, action, children, className, bodyClassName,
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cx("rounded-card border border-subtle bg-surface shadow-card", className)}>
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 border-b border-subtle px-4 py-2.5">
          <h2 className="text-heading text-primary">{title}</h2>
          {action}
        </header>
      )}
      <div className={cx("p-4", bodyClassName)}>{children}</div>
    </section>
  );
}

/** Sayfalarin ortak genislik ve responsive dis bosluk cercevesi. */
export function PageFrame({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cx("mx-auto w-full max-w-[1600px] px-4 py-5 sm:px-5 lg:px-6", className)}>
      {children}
    </div>
  );
}

/** Sayfa basligi; ana eylemi icerikle ayni hizada tutar. */
export function PageHeader({
  eyebrow, title, action,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  action?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-3">
      <div>
        {eyebrow && <p className="label-caps">{eyebrow}</p>}
        <h1 className="mt-1 font-serif text-title text-primary">{title}</h1>
      </div>
      {action}
    </header>
  );
}

/**
 * Icerik bolumu. Varsayilani KUTU: 1px kenarlik + beyaz yuzey + cok hafif
 * kabartma. Duz yatay ayraclarla kurulan onceki duzende bolumler birbirine
 * karisiyordu; kutu sinirlari "anca secilen" ama net bir cerceve verir.
 *
 * `flat` yalnizca zaten bir kutunun (Surface/Panel/popover) icindeyken --
 * ic ice kutu cizmemek icin.
 */
export function Section({
  title, hint, action, children, className, bodyClassName, flat = false,
}: {
  title?: ReactNode;
  hint?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  flat?: boolean;
}) {
  const head = title || hint || action;
  return (
    <section
      className={cx(
        !flat && "rounded-card border border-subtle bg-surface shadow-card",
        className,
      )}
    >
      {head && (
        <header
          className={cx(
            "flex min-h-8 flex-wrap items-center gap-x-3 gap-y-1 border-b border-subtle",
            flat ? "mb-2.5 px-0 pb-2" : "px-3.5 py-2",
          )}
        >
          {title && <h2 className="label-caps shrink-0 text-secondary">{title}</h2>}
          <span className="min-w-2 flex-1" />
          {hint && <span className="text-meta text-muted">{hint}</span>}
          {action}
        </header>
      )}
      <div className={cx(!flat && "px-3.5 py-3", bodyClassName)}>{children}</div>
    </section>
  );
}

/** Yalniz gercek gruplama gerektiren form, pane ve katman yuzeyi. */
export function Surface({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("rounded-card border border-subtle bg-surface shadow-card", className)}>{children}</div>;
}

/** Tek tek kart kullanmadan sayisal ozeti yatay ayiraclarla verir. */
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
  label, value, hint, href,
}: {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  /** Verilirse sayi kutusu o sayfaya giden bir baglantiya donusur. */
  href?: string;
}) {
  const body = (
    <>
      <div className="numeral truncate text-[24px] leading-none text-primary transition-colors group-hover:text-accent">
        {value}
      </div>
      <div className="mt-1 truncate text-meta text-secondary transition-colors group-hover:text-accent">
        {label}
      </div>
      {hint && <div className="truncate text-meta text-muted">{hint}</div>}
    </>
  );
  const shell = "min-w-0 px-3.5 py-3 sm:px-4";

  return href ? (
    <a href={href} className={cx(shell, "group block")}>{body}</a>
  ) : (
    <div className={shell}>{body}</div>
  );
}

/** Arama, filtre, siralama ve ana eylemlerin tek responsive seridi. */
export function Toolbar({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cx("flex flex-wrap items-center gap-2 border-y border-subtle py-2.5", className)}>
      {children}
    </div>
  );
}

/** Ince ayiracli veri satirlari. Cerceveyi saran kutu (Section) verir. */
export function RowList({
  children, className, as: Component = "div", onKeyDown,
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "ul" | "ol";
  onKeyDown?: React.KeyboardEventHandler<HTMLElement>;
}) {
  return (
    <Component
      className={cx("divide-y divide-subtle", className)}
      onKeyDown={onKeyDown}
    >
      {children}
    </Component>
  );
}

/**
 * Bolum basligi: kucuk kapital etiket + sayfayi bolen ince cizgi.
 * Today ve liste sayfalari hiyerarsiyi bununla kurar, kart icine almadan.
 */
export function SectionHeader({
  label, hint, action,
}: {
  label: string;
  hint?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="mb-3 flex items-baseline gap-3">
      <span className="label-caps">{label}</span>
      <span className="h-px flex-1 bg-subtle" />
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

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  primary:   "border-primary bg-primary text-canvas hover:opacity-90",
  secondary: "border-strong bg-surface text-primary hover:bg-surface-hover",
  ghost:     "border-transparent bg-transparent text-secondary hover:bg-surface-hover hover:text-primary",
  danger:    "border-danger-border bg-danger-surface text-danger hover:brightness-95",
};

export function Button({
  children, onClick, variant = "secondary", disabled, title, type = "button", size = "md", className, autoFocus,
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
}) {
  return (
    <button
      type={type}
      title={title}
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
  children, onClick, title, disabled, tone = "neutral", className,
}: {
  children: ReactNode;
  onClick?: () => void;
  title: string;
  disabled?: boolean;
  tone?: "neutral" | "danger";
  className?: string;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
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
  value, onChange, placeholder, disabled, type = "text", className, autoFocus, onKeyDown,
  onBlur, ariaLabel,
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
  value, onChange, children, disabled, className, ariaLabel, id,
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
  label, children, hint, className,
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

export function Textarea({
  value, onChange, placeholder, rows = 3, className, onBlur,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
  className?: string;
  onBlur?: (value: string) => void;
}) {
  return (
    <textarea
      value={value}
      rows={rows}
      placeholder={placeholder}
      onBlur={(e) => onBlur?.(e.target.value)}
      onChange={(e) => onChange(e.target.value)}
      className={cx(
        "w-full resize-y rounded-control border border-subtle bg-surface px-3 py-2 text-body text-primary",
        "outline-none placeholder:text-muted focus:border-accent focus:ring-1 focus:ring-accent",
        className,
      )}
    />
  );
}

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded border border-strong bg-surface px-1.5 py-0.5 font-sans text-[10.5px] leading-none text-muted">
      {children}
    </kbd>
  );
}

/* ══════════════════════════════════════════════════════════════════════
   Gosterim
   ══════════════════════════════════════════════════════════════════════ */

type BadgeTone = "neutral" | "warn" | "ok" | "accent" | "danger";

const BADGE_STYLES: Record<BadgeTone, string> = {
  neutral: "border-subtle bg-surface text-muted",
  accent:  "border-accent-border bg-accent-surface text-accent",
  ok:      "border-ok-border bg-ok-surface text-ok",
  warn:    "border-warn-border bg-warn-surface text-warn",
  danger:  "border-danger-border bg-danger-surface text-danger",
};

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: BadgeTone }) {
  return (
    <span className={cx("rounded border px-1.5 py-0.5 text-[10.5px] leading-4", BADGE_STYLES[tone])}>
      {children}
    </span>
  );
}

/**
 * Bos durum. Tek gri cumle degil: ne oldugunu soyler, ne yapilacagini gosterir.
 */
export function Empty({
  children, title, action, variant = "inline",
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
      {title && <p className="mb-1.5 font-serif text-title text-primary">{title}</p>}
      <p className="mx-auto max-w-md text-body text-secondary">{children}</p>
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-card border border-subtle bg-surface px-4 py-3">
      <div className="numeral text-[26px] leading-tight text-primary">{value}</div>
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

export interface Toast {
  id: number;
  message: string;
  tone: "neutral" | "ok" | "warn" | "danger";
  action?: { label: string; run: () => void };
}

interface ToastApi {
  push: (message: string, options?: { tone?: Toast["tone"]; action?: Toast["action"] }) => void;
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
    window.setTimeout(() => setToasts((current) => current.filter((t) => t.id !== id)), 6000);
  }, []);

  const api = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed bottom-5 left-1/2 z-[60] flex -translate-x-1/2 flex-col gap-2">
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
