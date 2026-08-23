import { afterEach, describe, expect, it, vi } from "vitest";
import { mutationErrorHandler } from "./queryClient";
import { subscribeGlobalToast } from "./ui";

describe("global mutation errors", () => {
  afterEach(() => vi.restoreAllMocks());

  it("emits one Turkish toast unless the mutation opts out", () => {
    const listener = vi.fn();
    const unsubscribe = subscribeGlobalToast(listener);

    mutationErrorHandler(new Error("boom"), undefined, undefined, { meta: undefined });
    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener.mock.calls[0][0].message).toContain("tamamlanamadı");

    mutationErrorHandler(new Error("quiet"), undefined, undefined, {
      meta: { silentError: true },
    });
    expect(listener).toHaveBeenCalledTimes(1);
    unsubscribe();
  });
});
