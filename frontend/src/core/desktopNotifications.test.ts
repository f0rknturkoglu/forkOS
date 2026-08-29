// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { hydrateEntityRegistry } from "./entityRegistry";
import {
  deliverDesktopNotification,
  desktopNotificationSupported,
  desktopPermission,
  desktopNotificationsEnabled,
  enableDesktopNotifications,
  setDesktopNotificationsEnabled,
} from "./desktopNotifications";

const store = new Map<string, string>();
vi.hoisted(() => {
  Object.defineProperty(globalThis, "localStorage", {
    value: {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => {
        store.set(k, v);
      },
      removeItem: (k: string) => {
        store.delete(k);
      },
      clear: () => {
        store.clear();
      },
      key: () => null,
      get length() {
        return store.size;
      },
    },
    configurable: true,
  });
});

class FakeNotification {
  static permission: NotificationPermission = "granted";
  static requestPermission = vi.fn(async () => "granted" as NotificationPermission);
  static instances: FakeNotification[] = [];
  onclick: ((event: Event) => void) | null = null;
  close = vi.fn();
  constructor(
    public title: string,
    public options?: NotificationOptions,
  ) {
    FakeNotification.instances.push(this);
  }
}

beforeEach(() => {
  store.clear();
  FakeNotification.instances = [];
  FakeNotification.permission = "granted";
  FakeNotification.requestPermission.mockReset();
  FakeNotification.requestPermission.mockResolvedValue("granted");
  setDesktopNotificationsEnabled(true);
  vi.stubGlobal("Notification", FakeNotification);
  hydrateEntityRegistry([
    {
      type: "opportunity",
      label: "Fırsat",
      label_plural: "Fırsatlar",
      route: "/opportunities?focus={id}",
      icon: "Target",
      searchable: true,
      linkable: true,
    },
  ]);
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("masaustu bildirimler (Faz 26)", () => {
  const item = (over: Partial<Parameters<typeof deliverDesktopNotification>[0]> = {}) => ({
    id: 7,
    kind: "test",
    title: "Önemli",
    body: "gövde",
    entity_id: "opp-1",
    entity_type: "opportunity",
    importance: 2,
    created_at: "2026-08-29T10:00:00Z",
    read_at: null,
    ...over,
  });

  it("duplicate teslim engellenir: ayni id bir kez OS bildirimi olur", () => {
    expect(deliverDesktopNotification(item())).toBe(true);
    expect(deliverDesktopNotification(item())).toBe(false);
    expect(FakeNotification.instances).toHaveLength(1);
  });

  it("dusuk onemli bildirim OS'e gonderilmez", () => {
    expect(deliverDesktopNotification(item({ importance: 1 }))).toBe(false);
    expect(FakeNotification.instances).toHaveLength(0);
  });

  it("izinsiz ortamda sessizce false (graceful fallback)", () => {
    FakeNotification.permission = "denied";
    expect(deliverDesktopNotification(item())).toBe(false);
    expect(deliverDesktopNotification(item())).toBe(false);
    expect(FakeNotification.instances).toHaveLength(0);
  });

  it("tiklayinca EntityTypeSpec rotasina gider", () => {
    deliverDesktopNotification(item());
    const instance = FakeNotification.instances[0];
    instance.onclick?.(new Event("click"));
    expect(window.location.hash).toBe("#/opportunities?focus=opp-1");
    expect(instance.close).toHaveBeenCalled();
  });

  it("reddedilen izin tekrar sorulmaz; granted ise tekrar istemez", async () => {
    FakeNotification.permission = "denied";
    expect(await enableDesktopNotifications()).toBe("denied");
    expect(FakeNotification.requestPermission).not.toHaveBeenCalled();
    expect(desktopPermission()).toBe("denied");

    FakeNotification.permission = "granted";
    expect(await enableDesktopNotifications()).toBe("granted");
    expect(FakeNotification.requestPermission).not.toHaveBeenCalled();
  });

  it("izin verildiginde teslimat tercihini de acar", async () => {
    setDesktopNotificationsEnabled(false);
    FakeNotification.permission = "default";
    FakeNotification.requestPermission.mockResolvedValueOnce("granted");

    expect(await enableDesktopNotifications()).toBe("granted");
    expect(desktopNotificationsEnabled()).toBe(true);
  });

  it("in-app teslimat kapaliyken OS bildirimi gonderilmez (izin dursa da)", () => {
    setDesktopNotificationsEnabled(false);
    expect(deliverDesktopNotification(item())).toBe(false);
    expect(FakeNotification.instances).toHaveLength(0);
  });

  it("constructor hatasinda id delivered'a YAZILMAZ -- sonraki turda yeniden denenir", () => {
    FakeNotification.permission = "granted";
    const original = FakeNotification;
    let failing = true;
    // Hatayi simule et: ilk kurulum patlar, sonraki calisir.
    vi.stubGlobal(
      "Notification",
      class extends original {
        constructor(title: string, options?: NotificationOptions) {
          if (failing) throw new Error("constructor fail");
          super(title, options);
        }
      },
    );
    expect(deliverDesktopNotification(item())).toBe(false);
    expect(FakeNotification.instances).toHaveLength(0);
    failing = false;
    expect(deliverDesktopNotification(item())).toBe(true);
    expect(FakeNotification.instances).toHaveLength(1);
  });

  it("desteklenmeyen ortam 'unsupported' doner", async () => {
    vi.stubGlobal("Notification", undefined);
    expect(desktopNotificationSupported()).toBe(false);
    expect(desktopPermission()).toBe("unsupported");
    expect(await enableDesktopNotifications()).toBe("unsupported");
  });
});
