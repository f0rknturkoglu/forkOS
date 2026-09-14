// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from "vitest";
import { FOCUS_PREFERENCES_EVENT, focusPreferences, setFocusPreferences } from "./preferences";

const storedValues = new Map<string, string>();
const storage: Storage = {
  get length() {
    return storedValues.size;
  },
  clear: () => storedValues.clear(),
  getItem: (key) => storedValues.get(key) ?? null,
  key: (index) => [...storedValues.keys()][index] ?? null,
  removeItem: (key) => storedValues.delete(key),
  setItem: (key, value) => storedValues.set(key, value),
};

describe("odak tercihleri", () => {
  beforeEach(() => {
    storage.clear();
    vi.stubGlobal("localStorage", storage);
  });

  it("temiz kurulumda 50/10 ve AMOLED varsayılanını kullanır", () => {
    expect(focusPreferences()).toEqual({ focusMinutes: 50, breakMinutes: 10, amoled: true });
  });

  it("değerleri sınırlar, saklar ve global dock'a bildirir", () => {
    const listener = vi.fn();
    window.addEventListener(FOCUS_PREFERENCES_EVENT, listener);

    setFocusPreferences({ focusMinutes: 75, breakMinutes: 15, amoled: false });

    expect(focusPreferences()).toEqual({ focusMinutes: 75, breakMinutes: 15, amoled: false });
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener(FOCUS_PREFERENCES_EVENT, listener);
  });
});
