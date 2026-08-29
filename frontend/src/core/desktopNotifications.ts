import { entityRoute } from "./entityRegistry";
import type { Notification } from "./types";

/**
 * Masaustu bildirim kapiyicisi (Faz 26).
 *
 * Mevcut `notification` tablosu + NotificationPanel kullanilir; ikinci
 * tablo yok. Web Notifications API uzerinden YALNIZCA yeni/okunmamis ve
 * yuksek onemli (importance >= 2) bildirimler OS bildirimi olur.
 *
 * - Izin ilk acilista ZORLA istenmez; ayarlardaki aciklamali aksiyonla
 *   istenir. Reddedilen izin tekrar tekrar sorulmaz.
 * - Teslim bilgisi localStorage'dadir (server truth degil): ayni
 *   bildirim birden fazla kez OS bildirimi uretmez.
 * - Tiklayinca EntityTypeSpec rotasina gidilir.
 * - Tarayici TAMAMEN kapaliyken yerel web uygulamasi bildirim gosteremez
 *   (dokumante edildi; SW push yok). Bu modul sayfa acikken calisir.
 */

const ASKED_KEY = "lifeos.desktopNotifAsked";
const DELIVERED_KEY = "lifeos.desktopNotifDelivered";
const ENABLED_KEY = "lifeos.desktopNotifEnabled";

/** In-app teslimat ac/kapat (Faz 34): izin geri alinamaz ama forkOS teslimatini
 *  kullanici durdurabilir. Varsayilan kapali -- kullanici acikca acar. */
export function desktopNotificationsEnabled(): boolean {
  try {
    return localStorage.getItem(ENABLED_KEY) === "1";
  } catch {
    return false;
  }
}

export function setDesktopNotificationsEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(ENABLED_KEY, enabled ? "1" : "0");
  } catch {
    /* localStorage yoksa hatirlanmaz; zararsiz */
  }
}

export function desktopNotificationSupported(): boolean {
  return typeof window !== "undefined" && typeof Notification !== "undefined";
}

export function desktopPermission(): NotificationPermission | "unsupported" {
  if (!desktopNotificationSupported()) return "unsupported";
  return Notification.permission;
}

export function hasAskedDesktopPermission(): boolean {
  try {
    return localStorage.getItem(ASKED_KEY) === "1";
  } catch {
    return false;
  }
}

/**
 * Izin ister. Reddedilmisse TEKRAR SORMAZ (tarayici ayarlarindan acilir).
 * Doner: "granted" | "denied" | "unsupported".
 */
export async function enableDesktopNotifications(): Promise<NotificationPermission | "unsupported"> {
  if (!desktopNotificationSupported()) return "unsupported";
  if (Notification.permission === "granted") return "granted";
  if (Notification.permission === "denied") return "denied";
  try {
    localStorage.setItem(ASKED_KEY, "1");
  } catch {
    /* localStorage yoksa sorma bayragi hatirlanmaz; zararsiz */
  }
  return Notification.requestPermission();
}

function readDelivered(): Set<string> {
  try {
    return new Set<string>(JSON.parse(localStorage.getItem(DELIVERED_KEY) ?? "[]"));
  } catch {
    return new Set();
  }
}

/**
 * OS bildirimi gonderir. Ayni id ikinci kez gonderilmez; yalnizca
 * importance >= 2. Tarayici API'si yoksa sessizce false.
 */
export function deliverDesktopNotification(item: Notification): boolean {
  if (!desktopNotificationSupported() || Notification.permission !== "granted") return false;
  if (!desktopNotificationsEnabled()) return false;
  if (item.importance < 2) return false;
  const delivered = readDelivered();
  if (delivered.has(String(item.id))) return false;
  let notification: globalThis.Notification;
  try {
    notification = new Notification(item.title, { body: item.body ?? undefined });
    notification.onclick = () => {
      if (item.entity_type && item.entity_id) {
        window.location.hash = entityRoute(item.entity_type, item.entity_id);
      }
      notification.close();
    };
  } catch {
    // Constructor basarisiz: id'yi delivered'a YAZMA -- sonraki turda yeniden
    // denenir (Faz 34). Basarili teslimden sonra bir daha gonderilmez.
    return false;
  }
  delivered.add(String(item.id));
  try {
    localStorage.setItem(DELIVERED_KEY, JSON.stringify([...delivered]));
  } catch {
    /* gecici teslim bilgisi; hata yutulur */
  }
  return true;
}
