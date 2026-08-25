// @vitest-environment jsdom

import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { matchRoutePath, useHashRoute } from "./router";

describe("hash route matching", () => {
  it("matches exact routes without accepting extra segments", () => {
    expect(matchRoutePath("/media", "/media")).toEqual(new URLSearchParams());
    expect(matchRoutePath("/media", "/media/media-1")).toBeNull();
    expect(matchRoutePath("/media/:id", "/media")).toBeNull();
  });

  it("decodes named path parameters without letting malformed escapes crash routing", () => {
    expect(matchRoutePath("/media/:id", "/media/media%2Fone")?.get("id")).toBe("media/one");
    expect(matchRoutePath("/media/:id", "/media/bad%escape")?.get("id")).toBe("bad%escape");
  });

  it("combines path parameters with current query parameters", () => {
    location.hash = "#/media/media%2Fone?tab=history";
    const { result } = renderHook(() => useHashRoute("/media/:id"));

    expect(result.current.path).toBe("/media/media%2Fone");
    expect(result.current.params.get("id")).toBe("media/one");
    expect(result.current.params.get("tab")).toBe("history");

    act(() => {
      location.hash = "#/media/media-2?tab=notes";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(result.current.params.get("id")).toBe("media-2");
    expect(result.current.params.get("tab")).toBe("notes");
  });
});
