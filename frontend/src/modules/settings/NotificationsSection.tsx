import { useState } from "react";
import { Bell, BellOff } from "lucide-react";
import { Button, Section, useToast } from "@/core/ui";
import { desktopPermission, enableDesktopNotifications, hasAskedDesktopPermission } from "@/core/desktopNotifications";

/**
 * Masaustu bildirim izni (Faz 26). Izin ilk acilista istenmez; bu
 * aciklamali aksiyonla istenir. Reddedilen izin tekrar sorulmaz.
 */
export function NotificationsSection() {
  const toast = useToast();
  const [state, setState] = useState(() => desktopPermission());

  async function enable() {
    const result = await enableDesktopNotifications();
    setState(result);
    if (result === "granted") {
      toast.push("Masaüstü bildirimleri açıldı — yeni önemli bildirimler OS olarak gelir.", { tone: "ok" });
    } else if (result === "denied") {
      toast.push("İzin reddedildi — tarayıcının site ayarlarından açabilirsin.", { tone: "warn" });
    } else {
      toast.push("Bu tarayıcı masaüstü bildirimi desteklemiyor.", { tone: "warn" });
    }
  }

  return (
    <Section title="Masaüstü bildirimleri">
      <p className="mb-2 text-meta text-muted">
        Yeni ve yüksek önemli bildirimler işletim sistemi bildirimi olarak gelir; in-app panel ile aynı kaynağı
        kullanır. Tarayıcı tamamen kapalıyken yerel uygulama bildirim gösteremez.
      </p>
      {state === "granted" ? (
        <p className="flex items-center gap-1.5 text-meta text-ok">
          <Bell size={13} /> İzin verildi — masaüstü bildirimleri açık.
        </p>
      ) : state === "denied" ? (
        <p className="flex items-center gap-1.5 text-meta text-warn">
          <BellOff size={13} /> İzin reddedildi; tarayıcının site ayarlarından açabilirsin.
        </p>
      ) : state === "unsupported" ? (
        <p className="text-meta text-muted">Bu tarayıcı masaüstü bildirimi desteklemiyor.</p>
      ) : (
        <Button size="sm" variant="primary" onClick={enable}>
          <Bell size={13} /> Masaüstü bildirimlerini aç
        </Button>
      )}
      {state !== "granted" && state !== "unsupported" && hasAskedDesktopPermission() && state === "denied" && (
        <p className="mt-1 text-meta text-muted">Tekrar sorulmaz — izin kalıcı olarak tarayıcıda saklanır.</p>
      )}
    </Section>
  );
}
