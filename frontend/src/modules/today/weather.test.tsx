// @vitest-environment jsdom

import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useWeather } from "./weather";

const harness = vi.hoisted(() => ({
  readStored: vi.fn(),
}));

vi.mock("@/core/api", () => ({ api: { get: vi.fn(), put: vi.fn() } }));
vi.mock("@/core/storage", () => ({ readStored: harness.readStored, writeStored: vi.fn() }));
vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(() => ({ data: undefined, isFetching: false, isError: false, refetch: vi.fn() })),
}));

describe("useWeather resilience", () => {
  afterEach(() => {
    harness.readStored.mockReset();
    Object.defineProperty(navigator, "geolocation", { configurable: true, value: undefined });
  });

  it("ignores malformed saved coordinates and degrades when geolocation is unavailable", async () => {
    harness.readStored.mockImplementation((key: string) => (key === "weather.lat" ? "{bozuk" : null));
    Object.defineProperty(navigator, "geolocation", { configurable: true, value: undefined });
    const { result } = renderHook(() => useWeather());

    expect(result.current.coords).toBeNull();
    await act(async () => result.current.requestLocation());
    expect(result.current.denied).toBe(true);
  });
});
