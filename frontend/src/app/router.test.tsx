// @vitest-environment jsdom

import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { findRouteMatch, matchRoutePath, navigate, useHashRoute } from "./router";

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

  it("preserves literal question marks after the query delimiter", () => {
    location.hash = "#/media/id?return=/search?tab=notes&x=1";
    const { result } = renderHook(() => useHashRoute("/media/:id"));

    expect(result.current.params.get("return")).toBe("/search?tab=notes");
    expect(result.current.params.get("x")).toBe("1");
  });

  it("prefers an exact static route over an earlier dynamic sibling", () => {
    const routes = [
      { path: "/media/:id", name: "detail" },
      { path: "/media/stats", name: "stats" },
    ];
    expect(findRouteMatch(routes, "/media/stats")?.name).toBe("stats");
  });

  it("replaces the current hash entry and notifies route subscribers exactly once", () => {
    history.replaceState(null, "", "#/media?focus=media%2Fone");
    const initialLength = history.length;
    const replaceState = vi.spyOn(history, "replaceState");
    const onHashChange = vi.fn();
    window.addEventListener("hashchange", onHashChange);
    const { result } = renderHook(() => useHashRoute("/media/:id"));

    act(() => navigate("/media/media%2Fone", { replace: true }));

    expect(location.hash).toBe("#/media/media%2Fone");
    expect(result.current.path).toBe("/media/media%2Fone");
    expect(result.current.params.get("id")).toBe("media/one");
    expect(history.length).toBe(initialLength);
    expect(onHashChange).toHaveBeenCalledOnce();
    expect(replaceState).toHaveBeenCalledWith(history.state, "", "#/media/media%2Fone");

    window.removeEventListener("hashchange", onHashChange);
    replaceState.mockRestore();
  });
});
