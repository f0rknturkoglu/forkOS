import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, OfflineWriteError } from "./api";

describe("offline API policy", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("navigator", { onLine: false });
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => ({ cached: true }) });
  });

  afterEach(() => vi.unstubAllGlobals());

  it("keeps GET available for the service-worker cache", async () => {
    await expect(api.get("/settings")).resolves.toEqual({ cached: true });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["post", () => api.post("/todos", {})],
    ["patch", () => api.patch("/todos/1", {})],
    ["put", () => api.put("/settings/theme", {})],
    ["delete", () => api.del("/todos/1")],
    ["upload", () => api.upload("/rss/import", {} as File)],
  ])("blocks %s before fetch", async (_name, write) => {
    await expect(write()).rejects.toBeInstanceOf(OfflineWriteError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
