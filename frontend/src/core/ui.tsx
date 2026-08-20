import type { ReactNode } from "react";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

export function Panel({
  title, action, children, className,
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cx("rounded-lg border border-neutral-800 bg-neutral-900/40", className)}
    >
      {(title || action) && (
        <header className="flex items-center justify-between border-b border-neutral-800 px-4 py-2">
          <h2 className="text-sm font-medium text-neutral-200">{title}</h2>
          {action}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Button({
  children, onClick, variant = "ghost", disabled, title, type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "ghost" | "primary" | "danger";
  disabled?: boolean;
  title?: string;
  type?: "button" | "submit";
}) {
  const styles = {
    ghost: "border-neutral-700 text-neutral-300 hover:bg-neutral-800",
    primary: "border-sky-700 bg-sky-800/60 text-sky-100 hover:bg-sky-700/60",
    danger: "border-red-900 text-red-300 hover:bg-red-950/60",
  }[variant];
  return (
    <button
      type={type}
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={cx(
        "rounded border px-2 py-1 text-xs transition",
        styles,
        disabled && "cursor-not-allowed opacity-40 hover:bg-transparent",
      )}
    >
      {children}
    </button>
  );
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "warn" | "ok" }) {
  const styles = {
    neutral: "border-neutral-700 text-neutral-400",
    warn: "border-amber-800 text-amber-400",
    ok: "border-emerald-800 text-emerald-400",
  }[tone];
  return (
    <span className={cx("rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wide", styles)}>
      {children}
    </span>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-6 text-center text-sm text-neutral-500">{children}</p>;
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 px-4 py-3">
      <div className="text-2xl font-semibold text-neutral-100">{value}</div>
      <div className="text-xs text-neutral-400">{label}</div>
      {hint && <div className="mt-1 text-[11px] text-neutral-600">{hint}</div>}
    </div>
  );
}

export function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diff / 60000);
  if (minutes < 1) return "az once";
  if (minutes < 60) return `${minutes} dk once`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} sa once`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} gun once`;
  return new Date(iso).toLocaleDateString("tr-TR");
}

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
