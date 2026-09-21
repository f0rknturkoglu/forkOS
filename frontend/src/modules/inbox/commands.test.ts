// @vitest-environment jsdom
/**
 * Gelen kutusu komutlarının hedefi (Polish 2 §57/§58).
 *
 * Komutlar `/today?triage=inbox`'a gidiyordu; öyle bir rota hiç olmadığı için
 * komut paletinden açınca "Böyle bir sayfa yok" ekranı çıkıyordu. Hedef artık
 * kanonik triyaj rotasıdır: `#/inbox`.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@/modules/inbox"; // komut kayitlari
import { findRouteMatch } from "@/app/router";
import { allCommands, allRoutes } from "@/core/registry";

const harness = vi.hoisted(() => ({ apiPost: vi.fn() }));

vi.mock("@/core/api", () => ({ api: { post: harness.apiPost }, qs: () => "" }));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));

// jsdom 30 + Node 26 localStorage getter sorunu: registry tercihleri okur.
vi.hoisted(() => {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => {
        store.set(key, value);
      },
      removeItem: (key: string) => {
        store.delete(key);
      },
      clear: () => store.clear(),
    },
  });
});

function command(id: string) {
  const found = allCommands().find((candidate) => candidate.id === id);
  if (!found) throw new Error(`komut kayitli degil: ${id}`);
  return found;
}

describe("gelen kutusu komutları", () => {
  beforeEach(() => {
    harness.apiPost.mockReset();
    vi.stubGlobal("crypto", { randomUUID: () => "uuid-1" });
    location.hash = "";
  });

  it("'Gelen kutusunu aç' kanonik /inbox rotasını açar", () => {
    command("inbox.open").run();

    expect(location.hash).toBe("#/inbox");
    expect(findRouteMatch(allRoutes(), "/inbox")).toBeDefined();
  });

  it("'Bağlantı kaydet' kaydedip triyaj yüzeyine gider", async () => {
    harness.apiPost.mockResolvedValue({ duplicate: false });

    await command("inbox.capture").run("https://example.com/yazi");

    expect(harness.apiPost).toHaveBeenCalledWith(
      "/capture",
      expect.objectContaining({ url: "https://example.com/yazi", collection: "inbox", client_uuid: "uuid-1" }),
    );
    expect(location.hash).toBe("#/inbox");
    expect(findRouteMatch(allRoutes(), "/inbox")).toBeDefined();
  });
});
