import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { deliverDesktopNotification, desktopPermission } from "@/core/desktopNotifications";
import type { Notification } from "@/core/types";

/**
 * NotificationPanel ile AYNI query key'ini izler (dedupe); yeni yuksek
 * onemli bildirimleri OS bildirimine tasir. Kendisi hicbir sey cizmez.
 * Izin yalnizca ayarlardaki aciklamali aksiyonla istenir (Faz 26).
 */
export function DesktopNotificationBridge() {
  const { data: items = [] } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.get<Notification[]>("/notifications"),
    refetchInterval: 60_000,
  });

  useEffect(() => {
    if (desktopPermission() !== "granted") return;
    const unread = items.filter((item) => !item.read_at);
    for (const item of unread) {
      deliverDesktopNotification(item);
    }
  }, [items]);

  return null;
}
