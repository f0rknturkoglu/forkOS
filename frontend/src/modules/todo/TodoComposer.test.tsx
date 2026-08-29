// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { localDateKey } from "@/lib/date";
import { TodoComposer } from "./TodoComposer";

// jsdom 30 + Node 26'da window.localStorage getter'i undefined donuyor; test
// icin bellek ici bir localStorage tanimliyoruz. Component SSR-safe oldugu icin
// node ortaminda (polyfill'siz renderToStaticMarkup) da calisir.
vi.hoisted(() => {
  const store = new Map<string, string>();
  const storage: Storage = {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key) => store.get(key) ?? null,
    key: (index) => [...store.keys()][index] ?? null,
    removeItem: (key) => {
      store.delete(key);
    },
    setItem: (key, value) => {
      store.set(key, String(value));
    },
  };
  Object.defineProperty(globalThis, "localStorage", {
    value: storage,
    configurable: true,
    writable: true,
  });
});

const harness = vi.hoisted(() => ({
  apiPost: vi.fn(),
  invalidate: vi.fn(),
}));

vi.mock("@/core/api", () => ({
  api: { post: harness.apiPost },
}));
vi.mock("@/lib/hooks", () => ({
  useOnline: () => true,
  useToast: () => ({ push: vi.fn() }),
}));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn((options: { mutationFn: () => unknown; onSuccess?: () => void }) => ({
    isPending: false,
    mutate: async () => {
      await options.mutationFn?.();
      options.onSuccess?.();
    },
  })),
}));

function openComposer() {
  render(<TodoComposer />);
  const field = screen.getByLabelText("Görev başlığı");
  fireEvent.focus(field);
  return field;
}

describe("TodoComposer bugune al", () => {
  beforeEach(() => {
    localStorage.clear();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
  });
  afterEach(() => cleanup());

  it("işaretliyken POST /todos gövdesine Istanbul gunu plan_day olarak gider", async () => {
    const field = openComposer();
    fireEvent.change(field, { target: { value: "Test görev" } });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Ekle" }));

    await waitFor(() => expect(harness.apiPost).toHaveBeenCalled());
    const [url, body] = harness.apiPost.mock.calls[0];
    expect(url).toBe("/todos");
    expect(body.plan_day).toBe(localDateKey(new Date()));
    // Gorev + plan tek istekte yazildi; iki olay da bildirilir (kural 14).
    expect(harness.invalidate).toHaveBeenCalledWith("todo.write", "plan.write");
  });

  it("işaretsizken plan_day gövdede YOK", async () => {
    const field = openComposer();
    fireEvent.change(field, { target: { value: "Test görev" } });
    fireEvent.click(screen.getByRole("button", { name: "Ekle" }));

    await waitFor(() => expect(harness.apiPost).toHaveBeenCalled());
    const [, body] = harness.apiPost.mock.calls[0];
    expect(body).not.toHaveProperty("plan_day");
  });

  it("son secim localStorage'a yazilir ve bir sonraki acilista hatirlanir", () => {
    const first = render(<TodoComposer />);
    fireEvent.focus(first.getByLabelText("Görev başlığı"));
    const checkbox = () => screen.getByRole("checkbox") as HTMLInputElement;

    // Varsayilan KAPALI.
    expect(checkbox().checked).toBe(false);

    fireEvent.click(checkbox());
    expect(checkbox().checked).toBe(true);
    expect(localStorage.getItem("todo.planToday")).toBe("1");

    // Tekrar render -- tercih korunmus olarak acilir.
    first.unmount();
    render(<TodoComposer />);
    fireEvent.focus(screen.getByLabelText("Görev başlığı"));
    expect(screen.getByRole("checkbox") as HTMLInputElement).toHaveProperty("checked", true);

    // Kapatinca tercih "0" olur.
    fireEvent.click(screen.getByRole("checkbox"));
    expect(localStorage.getItem("todo.planToday")).toBe("0");
  });
});
