/**
 * Graf sayfasi: odak/derinlik URL'den okunur ve ogrenmeye donuste secili konu
 * (`?focus=`) korunur.
 */
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GraphPage } from "./GraphPage";

const harness = vi.hoisted(() => ({ routeParams: "" }));

vi.mock("@/app/router", () => ({
  useHashRoute: () => ({ path: "/graph", params: new URLSearchParams(harness.routeParams) }),
  navigate: vi.fn(),
}));
vi.mock("@/core/GraphView", () => ({
  GraphView: ({ focus, depth }: { focus?: string; depth: number }) => (
    <div data-testid="graph">{`${focus ?? "all"}|${depth}`}</div>
  ),
}));

beforeEach(() => {
  harness.routeParams = "";
});

describe("GraphPage", () => {
  it("odakli graf derinligiyle acilir ve ogrenmeye donus odagi korur", () => {
    harness.routeParams = "focus=t1";
    const markup = renderToStaticMarkup(<GraphPage />);

    expect(markup).toContain('href="#/learning?focus=t1"');
    expect(markup).toContain("t1|2");
    expect(markup).toContain("Tüm graf");
  });

  it("odak yoksa tum graf ve odaksiz donus bagi", () => {
    const markup = renderToStaticMarkup(<GraphPage />);

    expect(markup).toContain('href="#/learning"');
    expect(markup).toContain("all|2");
    expect(markup).not.toContain("Tüm graf");
  });

  it("bozuk derinlik degerini varsayilana indirir", () => {
    harness.routeParams = "focus=t1&depth=abc";
    expect(renderToStaticMarkup(<GraphPage />)).toContain("t1|2");
  });
});
