// @vitest-environment jsdom
import { QueryClient, QueryClientProvider, onlineManager } from "@tanstack/react-query";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useWeather } from "./weather";
let calls: string[] = [];
let preferences: Record<string, unknown> = {};
let failed = false;
const clients: QueryClient[] = [];
function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  clients.push(client);
  return {
    client,
    Wrapper: ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  };
}
beforeEach(() => {
  calls = [];
  preferences = {};
  failed = false;
  localStorage.clear();
  onlineManager.setOnline(true);
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const path = new URL(String(input), "http://localhost").pathname;
      calls.push(path);
      const body =
        path === "/api/settings"
          ? preferences
          : path === "/api/weather/geocode"
            ? { name: "Berlin" }
            : { current: { temperature_2m: 19, weather_code: 0 }, daily: { time: [] } };
      return new Response(JSON.stringify(body), {
        status: failed && path.includes("forecast") ? 503 : 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
});
afterEach(() => {
  cleanup();
  clients.splice(0).forEach((c) => c.clear());
  vi.unstubAllGlobals();
  onlineManager.setOnline(true);
  Object.defineProperty(navigator, "geolocation", { configurable: true, value: undefined });
});
it("unconfigured launch performs no forecast or geolocation request", async () => {
  const geo = vi.fn();
  Object.defineProperty(navigator, "geolocation", { configurable: true, value: { getCurrentPosition: geo } });
  const { Wrapper } = setup();
  renderHook(() => useWeather(), { wrapper: Wrapper });
  await waitFor(() => expect(calls).toEqual(["/api/settings"]));
  expect(geo).not.toHaveBeenCalled();
});
it("server saved city loads and settings changes update location", async () => {
  preferences = { "weather.lat": 41, "weather.lon": 29, "weather.location": "İstanbul" };
  const { Wrapper, client } = setup();
  const { result } = renderHook(() => useWeather(), { wrapper: Wrapper });
  await waitFor(() => expect(result.current.data).toBeTruthy());
  expect(result.current.place).toBe("İstanbul");
  act(() => client.setQueryData(["settings"], { "weather.lat": 52, "weather.lon": 13, "weather.location": "Berlin" }));
  await waitFor(() => expect(result.current.coords?.lat).toBe(52));
});
it("hidden configured weather never fetches", async () => {
  localStorage.setItem("forkos.weather.lat", "41");
  localStorage.setItem("forkos.weather.lon", "29");
  const { Wrapper } = setup();
  renderHook(() => useWeather({ displayed: false }), { wrapper: Wrapper });
  await act(async () => {});
  expect(calls).toEqual([]);
});
it("location is requested only on explicit action; denied permission is non-blocking", async () => {
  const geo = vi.fn((_ok, deny) => deny());
  Object.defineProperty(navigator, "geolocation", { configurable: true, value: { getCurrentPosition: geo } });
  const { Wrapper } = setup();
  const { result } = renderHook(() => useWeather({ displayed: false }), { wrapper: Wrapper });
  expect(geo).not.toHaveBeenCalled();
  act(() => result.current.requestLocation());
  expect(geo).toHaveBeenCalledTimes(1);
  expect(result.current.denied).toBe(true);
  expect(calls).toEqual([]);
});
it("explicit successful geolocation saves existing preferences", async () => {
  const geo = vi.fn((ok) => ok({ coords: { latitude: 52, longitude: 13 } }));
  Object.defineProperty(navigator, "geolocation", { configurable: true, value: { getCurrentPosition: geo } });
  const { Wrapper } = setup();
  const { result } = renderHook(() => useWeather({ displayed: false }), { wrapper: Wrapper });
  await act(async () => result.current.requestLocation());
  await waitFor(() => expect(result.current.asking).toBe(false));
  expect(result.current.coords).toEqual({ lat: 52, lon: 13 });
  expect(calls).toContain("/api/settings/weather.lat");
  expect(calls).not.toContain("/api/weather/forecast");
});
it("forecast failure leaves a recoverable error", async () => {
  failed = true;
  preferences = { "weather.lat": 41, "weather.lon": 29 };
  const { Wrapper } = setup();
  const { result } = renderHook(() => useWeather(), { wrapper: Wrapper });
  await waitFor(() => expect(result.current.isError).toBe(true));
});
it("offline preserves cache without a request", async () => {
  onlineManager.setOnline(false);
  const { Wrapper, client } = setup();
  client.setQueryData(["settings"], { "weather.lat": 41, "weather.lon": 29 });
  client.setQueryData(["weather", 41, 29], { current: { temperature_2m: 19 } });
  const { result } = renderHook(() => useWeather(), { wrapper: Wrapper });
  await act(async () => {});
  expect(calls).toEqual([]);
  expect(result.current.data?.current.temperature_2m).toBe(19);
});
