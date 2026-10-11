// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { SummaryMetric, TodaySummary } from "./TodaySummary";
afterEach(cleanup);
let count = 0;
const Stats = () => (
  <>
    <SummaryMetric label="Bekleyen" value={count} />
    <SummaryMetric label="Yükleniyor" value="–" />
  </>
);
it("counts live values while closed, omits zero, and keeps disclosure keyboard behavior", async () => {
  count = 0;
  const view = render(<TodaySummary stats={[Stats]} />);
  expect(screen.queryByLabelText(/toplam/)).toBeNull();
  count = 3;
  view.rerender(<TodaySummary stats={[Stats]} />);
  await screen.findByLabelText("3 toplam");
  const summary = screen.getByText("Günlük özet");
  const details = summary.closest("details")!;
  expect(details.open).toBe(false);
  fireEvent.click(summary);
  expect(details.open).toBe(true);
  fireEvent.keyDown(summary, { key: "Escape" });
  expect(details.open).toBe(false);
  expect(document.activeElement).toBe(summary);
  count = 0;
  view.rerender(<TodaySummary stats={[Stats]} />);
  await waitFor(() => expect(screen.queryByLabelText(/toplam/)).toBeNull());
});
