import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { Button, Modal } from "./ui";

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
  const active = useRef<Pending | null>(null);

  useEffect(() => {
    show = (next) => {
      // A second request cannot replace an unanswered confirmation promise.
      if (active.current) return next.resolve(false);
      active.current = next;
      setPending(next);
    };
    return () => {
      show = null;
      active.current?.resolve(false);
      active.current = null;
    };
  }, []);

  function close(ok: boolean) {
    active.current?.resolve(ok);
    active.current = null;
    setPending(null);
  }

  if (!pending) return null;

  return (
    <Modal
      open
      role="alertdialog"
      title={pending.title}
      onClose={() => close(false)}
      footer={
        <div className="flex flex-wrap justify-end gap-2">
          <Button onClick={() => close(false)}>{pending.cancelLabel ?? "Vazgeç"}</Button>
          <Button variant={pending.tone === "danger" ? "danger" : "primary"} onClick={() => close(true)}>
            {pending.confirmLabel}
          </Button>
        </div>
      }
    >
      {pending.body && <div className="text-body text-secondary">{pending.body}</div>}
    </Modal>
  );
}
