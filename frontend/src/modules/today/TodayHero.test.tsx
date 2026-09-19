// @vitest-environment jsdom

import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TodayHero } from "./TodayHero";

const harness = vi.hoisted(() => ({
  refetch: vi.fn(),
  weather: {
    coords: null as { lat: number; lon: number } | null,
    data: undefined,
    isError: false,
    refetch: vi.fn(),
    asking: false,
    denied: false,
    place: null as string | null,
    requestLocation: vi.fn(),
  },
}));

vi.mock("./weather", () => ({
  useWeather: () => harness.weather,
  weatherIcon: () => () => null,
  weatherLabel: () => "Açık",
}));

describe("TodayHero", () => {
  afterEach(() => {
    vi.useRealTimers();
    harness.weather.coords = null;
    harness.weather.isError = false;
    harness.weather.refetch.mockReset();
  });

  it("uses the app timezone at the Istanbul day boundary", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-14T21:30:00Z"));
    render(<TodayHero />);

    expect(screen.getByText("İyi geceler")).toBeTruthy();
    expect(screen.getByText(/15 Ocak/)).toBeTruthy();
    expect(screen.getByText(/00:30/)).toBeTruthy();
  });

  it("exposes a forecast retry rather than a permanent loading message", () => {
    harness.weather.coords = { lat: 41, lon: 29 };
    harness.weather.isError = true;
    render(<TodayHero />);

    fireEvent.click(screen.getByRole("button", { name: "Yeniden dene" }));
    expect(harness.weather.refetch).toHaveBeenCalledTimes(1);
  });

  it("saati saniyede degil dakika sinirinda gunceller", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-14T21:30:05Z"));
    const { container } = render(<TodayHero />);

    const clock = () => container.querySelector("time")?.textContent ?? "";
    const first = clock();
    expect(first).toMatch(/^\d{2}:\d{2}$/);
    expect(first).not.toMatch(/:\d{2}:\d{2}/);

    // Saniyelik bir interval her saniye yeniden render ederdi; saniye
    // gosterilmedigi icin dakika dolmadan saat DEGISMEMELI.
    act(() => vi.advanceTimersByTime(1000));
    expect(clock()).toBe(first);

    // Dakika sinirini gec: saat bir kez guncellenmeli.
    act(() => vi.advanceTimersByTime(60_000));
    expect(clock()).not.toBe(first);
  });
});
