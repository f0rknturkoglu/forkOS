import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Button, cx } from "./ui";

/**
 * Onay diyalogu.
 *
 * Neden imperatif: komut paletinin komutlari React agacinin DISINDA calisir
 * (registerModule icindeki run()), yani hook cagiramazlar. confirmDialog()
 * her yerden cagrilabilen bir promise dondurur; DialogHost onu ciziyor.
 *
 * Native confirm() yerine bu kullanilir -- tema, Turkce ve klavye bizde.
 */

interface ConfirmOptions {
  title: string;
  body?: ReactNode;
  /** Onay butonunun metni. Ne olacagini soylesin: "Sil", "Okundu işaretle". */
  confirmLabel: string;
  cancelLabel?: string;
  tone?: "neutral" | "danger";
}

type Pending = ConfirmOptions & { resolve: (ok: boolean) => void };

let show: ((pending: Pending) => void) | null = null;

export function confirmDialog(options: ConfirmOptions): Promise<boolean> {
  // Host takili degilse (test, SSR) engellemek yerine reddet.
  if (!show) return Promise.resolve(false);
  return new Promise<boolean>((resolve) => show?.({ ...options, resolve }));
}

export function DialogHost() {
  const [pending, setPending] = useState<Pending | null>(null);

  useEffect(() => {
    show = setPending;
    return () => {
      show = null;
    };
  }, []);

  useEffect(() => {
    if (!pending) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        close(false);
      }
    };
    document.addEventListener("keydown", onKey, true);
    return () => document.removeEventListener("keydown", onKey, true);
  });

  function close(ok: boolean) {
    pending?.resolve(ok);
    setPending(null);
  }

  if (!pending) return null;

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center bg-[color:var(--overlay-scrim)] p-6"
      onClick={() => close(false)}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-label={pending.title}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-overlay border border-strong bg-surface p-6 shadow-overlay"
      >
        <h2 className={cx(" text-title", pending.tone === "danger" ? "text-danger" : "text-primary")}>
          {pending.title}
        </h2>
        {pending.body && <div className="mt-2 text-body text-secondary">{pending.body}</div>}
        <div className="mt-5 flex justify-end gap-2">
          <Button onClick={() => close(false)}>{pending.cancelLabel ?? "Vazgeç"}</Button>
          <Button autoFocus variant={pending.tone === "danger" ? "danger" : "primary"} onClick={() => close(true)}>
            {pending.confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
