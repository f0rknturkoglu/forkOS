// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { GoalCoachingFacts } from "./GoalCoachingFacts";

afterEach(cleanup);

describe("Goal assistant canonical facts", () => {
  it("renders recorded progress independently of model interpretation", () => {
    const { rerender } = render(
      <GoalCoachingFacts
        value={{
          percent: 67,
          completed: 2,
          total: 3,
          outcome_percent: null,
          remaining: ["Yanlışları incele"],
          actions: ["Yanlışları incele"],
        }}
      />,
    );
    expect(screen.getByText(/Çalışma ilerlemesi: %67/)).toBeTruthy();
    expect(screen.getByText(/2\/3 görev tamamlandı/)).toBeTruthy();
    expect(screen.getByText(/Henüz ölçülmedi/)).toBeTruthy();
    rerender(<GoalCoachingFacts value={{ percent: 100, completed: 3, total: 3, outcome_percent: null }} />);
    expect(screen.getByText(/Çalışma ilerlemesi: %100/)).toBeTruthy();
    expect(screen.getByText(/Henüz ölçülmedi/)).toBeTruthy();
    expect(screen.queryByText(/Bekleyen/)).toBeNull();
  });

  it("distinguishes missing scope and measured outcome", () => {
    render(
      <GoalCoachingFacts value={{ percent: null, completed: 0, total: 0, outcome_percent: 50, truncated: true }} />,
    );
    expect(screen.getByText(/Henüz bilinmiyor/)).toBeTruthy();
    expect(screen.getByText(/Gerçek sonuç: %50/)).toBeTruthy();
    expect(screen.getByText(/sınırlı bir bölümünü/)).toBeTruthy();
  });

  it("keeps historical V1 replies usable when facts were not recorded", () => {
    const { container } = render(<GoalCoachingFacts value={undefined} />);
    expect(container.textContent).toBe("");
  });
});
