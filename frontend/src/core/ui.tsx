import type { ReactNode } from "react";
import { createContext, forwardRef, useCallback, useContext, useEffect, useMemo, useState } from "react";

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
    return () => {
      themeListeners.delete(setLocal);
    };
  }, []);
  return [theme, applyTheme];
}

/* ══════════════════════════════════════════════════════════════════════
   Yuzeyler
   ══════════════════════════════════════════════════════════════════════ */

/** Sayfalarin ortak genislik ve responsive dis bosluk cercevesi. */
export function PageFrame({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("mx-auto w-full max-w-[1600px] px-4 py-5 sm:px-5 lg:px-6", className)}>{children}</div>;
}

/** Sayfa basligi; ana eylemi icerikle ayni hizada tutar. */
export function PageHeader({ eyebrow, title, action }: { eyebrow?: ReactNode; title: ReactNode; action?: ReactNode }) {
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
  title,
  hint,
  action,
  children,
  className,
  bodyClassName,
  flat = false,
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
    <section className={cx(!flat && "rounded-card border border-subtle bg-surface shadow-card", className)}>
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
 * Bolum basligi: kucuk kapital etiket + sayfayi bolen ince cizgi.
 * Today ve liste sayfalari hiyerarsiyi bununla kurar, kart icine almadan.
 */
export function SectionHeader({ label, hint, action }: { label: string; hint?: ReactNode; action?: ReactNode }) {
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
  primary: "border-primary bg-primary text-canvas hover:opacity-90",
  secondary: "border-strong bg-surface text-primary hover:bg-surface-hover",
  ghost: "border-transparent bg-transparent text-secondary hover:bg-surface-hover hover:text-primary",
  danger: "border-danger-border bg-danger-surface text-danger hover:brightness-95",
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
}) {
  return (
    <button
      type={type}
      title={title}
      aria-label={ariaLabel ?? title}
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
  className,
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

export function Textarea({
  value,
  onChange,
  placeholder,
  rows = 3,
  className,
  onBlur,
  disabled,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
  className?: string;
  onBlur?: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <textarea
      value={value}
      rows={rows}
      placeholder={placeholder}
      disabled={disabled}
      onBlur={(e) => onBlur?.(e.target.value)}
      onChange={(e) => onChange(e.target.value)}
      className={cx(
        "w-full resize-y rounded-control border border-subtle bg-surface px-3 py-2 text-body text-primary",
        "outline-none placeholder:text-muted focus:border-accent focus:ring-1 focus:ring-accent",
        disabled && "cursor-not-allowed opacity-50",
        className,
      )}
    />
  );
}

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
  className,
}: {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  ariaLabel?: string;
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
      onChange={(e) => onChange(Number(e.target.value))}
      className={cx("h-4 w-full cursor-pointer accent-accent", className)}
    />
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
    onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
    className?: string;
  }
>(function FileInput({ accept, onChange, className }, ref) {
  return <input ref={ref} type="file" accept={accept} onChange={onChange} className={cx("hidden", className)} />;
});

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

type ChipTone = "neutral" | "accent" | "ok" | "warn" | "danger";
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
  children: ReactNode;
  variant?: ChipVariant;
  icon?: ReactNode;
  size?: "xs" | "sm";
};
type ChipProps = ChipBase & ({ tone?: ChipTone; identity?: never } | { identity: string; tone?: never });

/**
 * Tek chip/rozet bileşeni.
 * - `tone`    => semantik anlam (durum, oncelik, saglik).
 * - `identity`=> kimlik rengi ("kind-movie" | "src-tmdb" | "feed-hn").
 * Ikisi ayni anda verilemez (tip duzeyinde engellenir).
 */
export function Chip({ children, variant = "soft", tone, identity, icon, size = "sm" }: ChipProps) {
  const style = identity
    ? (IDENTITY_STYLES[identity] ?? "border-subtle bg-surface text-secondary")
    : CHIP_STYLES[variant][tone ?? "neutral"];
  return (
    <span
      className={cx(
        "inline-flex shrink-0 items-center gap-1 rounded border font-medium leading-4",
        size === "xs" ? "px-1.5 py-px text-micro" : "px-2 py-0.5 text-micro",
        style,
      )}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </span>
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
      {title && <p className="mb-1.5 font-serif text-title text-primary">{title}</p>}
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
  push: (message: string, options?: { tone?: Toast["tone"]; action?: Toast["action"] }) => void;
}

type GlobalToastInput = {
  message: string;
  options?: { tone?: Toast["tone"]; action?: Toast["action"] };
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
    window.setTimeout(() => setToasts((current) => current.filter((t) => t.id !== id)), 6000);
  }, []);

  const api = useMemo(() => ({ push }), [push]);

  useEffect(() => subscribeGlobalToast(({ message, options }) => push(message, options)), [push]);

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
