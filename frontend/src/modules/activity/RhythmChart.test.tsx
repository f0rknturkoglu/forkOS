// @vitest-environment jsdom
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { RhythmChart } from "./RhythmChart";
import type { MonthlyPoint } from "@/core/types";

const SAMPLE_POINTS: MonthlyPoint[] = [
  { month: "2026-03", pomodoros: 10, todos: 15, bookmarks: 5, notes: 3, rss_read: 20, reviews: 2, applications: 1 },
  { month: "2026-04", pomodoros: 20, todos: 25, bookmarks: 8, notes: 4, rss_read: 30, reviews: 3, applications: 2 },
  { month: "2026-05", pomodoros: 0, todos: 0, bookmarks: 0, notes: 0, rss_read: 0, reviews: 0, applications: 0 },
];

describe("RhythmChart", () => {
  afterEach(cleanup);
  it("aylik hareket noktalarini render eder ve etiketleri gosterir", () => {
    render(<RhythmChart points={SAMPLE_POINTS} />);

    expect(screen.getByRole("img", { name: "Son ayların toplam hareketi" })).not.toBeNull();
    expect(screen.getByText("Mar '26")).not.toBeNull();
    expect(screen.getByText("Nis '26")).not.toBeNull();
    expect(screen.getByText("May '26")).not.toBeNull();
  });

  it("bar uzerine gelindiginde detayli aktivite dokumu popover'ini gosterir", () => {
    render(<RhythmChart points={SAMPLE_POINTS} />);

    const barContainers = screen.getAllByTestId("rhythm-month-bar");
    expect(barContainers.length).toBe(3);

    fireEvent.mouseEnter(barContainers[0]);
    expect(screen.getByText(/56 toplam hareket/i)).not.toBeNull();
    expect(screen.getByText(/10 Odak/i)).not.toBeNull();
    expect(screen.getByText(/15 Görev/i)).not.toBeNull();
  });

  it("kompakt modda sade gosterim yapar", () => {
    render(<RhythmChart points={SAMPLE_POINTS} compact />);
    expect(screen.getByRole("img")).not.toBeNull();
  });
});
