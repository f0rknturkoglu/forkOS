import { invalidateAfter } from "./invalidation";
import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Bell, BellOff, CheckCheck, X } from "lucide-react";
import { api } from "./api";
import { Empty, Popover, cx, relativeTime } from "./ui";
import type { Notification } from "./types";
import { entityRoute } from "./entityRegistry";

/**
 * Ust seritteki bildirim paneli.
 *
 * Bildirimler modul-ustu: kaynak koşumu, son tarih merdiveni ve fırsat özeti
 * hepsi tek /notifications ucundan gelir. Bu yuzden core'da duruyor, bir
 * modulun icinde degil.
 */

/** Bildirimin hedefi -- once entity turu (kayit defterinden), o yoksa tur. */
const ROUTE_FOR_KIND: [prefix: string, route: string][] = [
  ["opportunity", "/opportunities"],
  ["deadline", "/opportunities"],
  ["source", "/sources"],
  ["rss", "/rss"],
  ["media", "/media"],
];

export function notificationRoute(item: Notification): string {
  if (item.entity_type) {
    const route = entityRoute(item.entity_type, item.entity_id ?? "");
    if (route !== "#/") return route;
  }
  const match = ROUTE_FOR_KIND.find(([prefix]) => item.kind.startsWith(prefix));
  return match ? match[1] : "/activity";
}

/** importance 1..3 -> nokta rengi. 3 = aciliyet var. */
const DOT: Record<number, string> = { 1: "bg-icon", 2: "bg-warn", 3: "bg-danger" };

export function NotificationPanel() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const { data: items = [] } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.get<Notification[]>("/notifications"),
    refetchInterval: 60_000,
  });
  const unread = items.filter((item) => !item.read_at).length;

  const read = useMutation({
    mutationFn: (id: number) => api.post(`/notifications/${id}/read`),
    onSuccess: () => invalidateAfter("notification.write"),
  });
  const readAll = useMutation({
    mutationFn: () => api.post("/notifications/read-all"),
    onSuccess: () => invalidateAfter("notification.write"),
  });
  const dismiss = useMutation({
    mutationFn: (id: number) => api.post(`/notifications/${id}/dismiss`),
    onSuccess: () => invalidateAfter("notification.write"),
  });
  const dismissAll = useMutation({
    mutationFn: () => api.post("/notifications/dismiss-all"),
    onSuccess: () => invalidateAfter("notification.write"),
  });

  function openItem(item: Notification) {
    if (!item.read_at) read.mutate(item.id);
    location.hash = notificationRoute(item);
    setOpen(false);
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={unread > 0 ? `Bildirimler, ${unread} okunmamış` : "Bildirimler"}
        aria-expanded={open}
        title="Bildirimler"
        className={cx(
          "relative flex h-9 w-9 items-center justify-center rounded-control border transition",
          open
            ? "border-strong bg-surface-sunken text-primary"
            : "border-subtle bg-surface text-muted hover:bg-surface-hover hover:text-primary",
        )}
      >
        <Bell size={16} />
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-danger px-1 text-micro font-medium leading-none text-canvas">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      <Popover
        open={open}
        onClose={() => setOpen(false)}
        anchorRef={rootRef}
        role="dialog"
        ariaLabel="Bildirimler"
        className="right-0 top-11 w-[380px]"
      >
          <div className="flex items-center gap-3 border-b border-subtle px-4 py-3">
            <h2 className="text-heading text-primary">Bildirimler</h2>
            {unread > 0 && (
              <span className="rounded border border-accent-border bg-accent-surface px-1.5 py-0.5 text-micro leading-4 text-accent">
                {unread} yeni
              </span>
            )}
            <span className="flex-1" />
            {unread > 0 && (
              <button
                type="button"
                onClick={() => readAll.mutate()}
                disabled={readAll.isPending}
                className="flex items-center gap-1.5 text-meta text-muted transition hover:text-primary disabled:opacity-50"
              >
                <CheckCheck size={14} />
                Tümünü okundu işaretle
              </button>
            )}
            {items.length > 0 && (
              <button
                type="button"
                onClick={() => dismissAll.mutate()}
                disabled={dismissAll.isPending}
                className="flex items-center gap-1.5 text-meta text-muted transition hover:text-danger disabled:opacity-50"
              >
                <BellOff size={14} />
                Tümünü kapat
              </button>
            )}
          </div>

          <div className="max-h-[420px] overflow-y-auto">
            {items.length === 0 ? (
              <div className="px-4 py-8">
                <Empty>Bildirim yok. Kaynaklar yeni fırsat bulunca burada görünür.</Empty>
              </div>
            ) : (
              <ul>
                {items.map((item) => (
                  <li key={item.id} className="group relative border-b border-subtle last:border-b-0">
                    <button
                      type="button"
                      onClick={() => openItem(item)}
                      className={cx(
                        "flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-surface-hover",
                        !item.read_at && "bg-accent-surface/40",
                      )}
                    >
                      <span
                        className={cx("mt-1.5 h-2 w-2 shrink-0 rounded-full", DOT[item.importance] ?? DOT[1])}
                        aria-hidden
                      />
                      <span className="min-w-0 flex-1">
                        <span
                          className={cx(
                            "block text-body",
                            item.read_at ? "text-secondary" : "font-medium text-primary",
                          )}
                        >
                          {item.title}
                        </span>
                        {item.body && <span className="mt-0.5 block text-meta text-muted">{item.body}</span>}
                        <span className="mt-1 block text-meta text-muted">{relativeTime(item.created_at)}</span>
                      </span>
                    </button>
                    <button
                      type="button"
                      onClick={() => dismiss.mutate(item.id)}
                      aria-label="Bildirimi kaldır"
                      title="Kaldır"
                      className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-control text-muted opacity-0 transition hover:bg-surface-sunken hover:text-primary focus-visible:opacity-100 group-hover:opacity-100"
                    >
                      <X size={14} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
      </Popover>
    </div>
  );
}
