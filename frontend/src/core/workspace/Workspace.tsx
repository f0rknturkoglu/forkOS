import type { ReactNode } from "react";
import { cx } from "@/core/ui";

/**
 * AFFiNE esinli ortak çalışma yüzeyi.
 *
 * Sayfaların kendi grid, border ve scroll sözleşmelerini tekrar kurmasını
 * engeller. Mobilde bölmeler alt alta, masaüstünde tek uygulama yüzeyi olur.
 */
export function Workspace({
  rail,
  inspector,
  children,
  className,
  railAt = "md",
  railWidth = "default",
}: {
  rail?: ReactNode;
  inspector?: ReactNode;
  children: ReactNode;
  className?: string;
  railAt?: "md" | "lg";
  railWidth?: "default" | "wide";
}) {
  const columns = rail
    ? inspector
      ? railAt === "lg"
        ? railWidth === "wide"
          ? "lg:grid-cols-workspace-wide-rail xl:grid-cols-workspace-wide-three"
          : "lg:grid-cols-workspace-rail xl:grid-cols-workspace-three"
        : railWidth === "wide"
          ? "md:grid-cols-workspace-wide-rail xl:grid-cols-workspace-wide-three"
          : "md:grid-cols-workspace-rail xl:grid-cols-workspace-three"
      : railAt === "lg"
        ? railWidth === "wide"
          ? "lg:grid-cols-workspace-wide-rail"
          : "lg:grid-cols-workspace-rail"
        : railWidth === "wide"
          ? "md:grid-cols-workspace-wide-rail"
          : "md:grid-cols-workspace-rail"
    : inspector
      ? "lg:grid-cols-workspace-inspector"
      : "";

  return (
    <div
      className={cx(
        "grid min-h-workspace-body overflow-hidden rounded-card border border-subtle bg-surface shadow-card",
        columns,
        className,
      )}
    >
      {rail ? (
        <aside
          className={cx(
            "min-w-0 border-b border-subtle bg-surface-sunken",
            railAt === "lg" ? "lg:border-b-0 lg:border-r" : "md:border-b-0 md:border-r",
          )}
        >
          {rail}
        </aside>
      ) : null}
      <section className="flex min-h-0 min-w-0 flex-col">{children}</section>
      {inspector ? (
        <aside
          className={cx(
            "min-w-0 border-t border-subtle bg-surface-sunken",
            rail ? "md:col-span-2 xl:col-span-1 xl:border-t-0 xl:border-l" : "lg:border-t-0 lg:border-l",
          )}
        >
          {inspector}
        </aside>
      ) : null}
    </div>
  );
}

export function WorkspacePaneHeader({
  title,
  eyebrow,
  hint,
  action,
  children,
  wrapTitle = false,
}: {
  title: ReactNode;
  eyebrow?: ReactNode;
  hint?: ReactNode;
  action?: ReactNode;
  children?: ReactNode;
  wrapTitle?: boolean;
}) {
  return (
    <header className="shrink-0 border-b border-subtle bg-surface px-4 py-3">
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <div className="min-w-0 flex-1">
          {eyebrow ? <p className="label-caps mb-1 text-muted">{eyebrow}</p> : null}
          <h1 className={cx(wrapTitle ? "break-words" : "truncate", "text-heading text-primary")}>{title}</h1>
        </div>
        {hint ? <span className="text-meta tabular-nums text-muted">{hint}</span> : null}
        {action}
      </div>
      {children ? <div className="mt-3">{children}</div> : null}
    </header>
  );
}

export function WorkspaceRailContent({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("max-h-workspace-body space-y-4 overflow-y-auto p-3", className)}>{children}</div>;
}

export function WorkspaceRailGroup({
  label,
  hint,
  children,
}: {
  label: ReactNode;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section>
      <div className="mb-1.5 flex items-center gap-2 px-2">
        <h2 className="label-caps min-w-0 flex-1 truncate text-muted">{label}</h2>
        {hint ? <span className="text-meta tabular-nums text-muted">{hint}</span> : null}
      </div>
      <div className="space-y-0.5">{children}</div>
    </section>
  );
}

export function WorkspaceRailButton({
  label,
  count,
  active,
  icon,
  onClick,
}: {
  label: ReactNode;
  count?: ReactNode;
  active?: boolean;
  icon?: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-current={active ? "page" : undefined}
      onClick={onClick}
      className={cx(
        "flex h-8 w-full min-w-0 items-center gap-2 rounded-control px-2 text-left text-body transition",
        active
          ? "bg-surface-selected font-medium text-primary"
          : "text-secondary hover:bg-surface-hover hover:text-primary",
      )}
    >
      {icon ? <span className="shrink-0 text-icon">{icon}</span> : null}
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {count !== undefined ? <span className="text-meta tabular-nums text-muted">{count}</span> : null}
    </button>
  );
}

export function WorkspaceScrollArea({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("min-h-0 flex-1 overflow-y-auto", className)}>{children}</div>;
}

export function WorkspaceInspectorContent({
  title,
  hint,
  children,
}: {
  title: ReactNode;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="max-h-workspace-body overflow-y-auto p-3">
      <div className="mb-3 flex min-w-0 items-center gap-2 px-1">
        <h2 className="label-caps min-w-0 flex-1 truncate text-secondary">{title}</h2>
        {hint ? <span className="text-meta text-muted">{hint}</span> : null}
      </div>
      {children}
    </div>
  );
}
