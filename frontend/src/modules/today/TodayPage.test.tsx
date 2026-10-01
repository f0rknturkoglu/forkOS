import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { TodayPlacement } from "@/core/types";
import { HomeGrid } from "./TodayPage";
import type { TodayWidgetView } from "@/core/registry";

function view(id: string, core?: TodayPlacement, placement?: TodayPlacement): TodayWidgetView {
  const component = () => <span>{id}</span>;
  return { id, title: id, moduleId: "test", widget: { id, title: id, component, core, placement, order: 1 } };
}

const page = (views: TodayWidgetView[]) => renderToStaticMarkup(<HomeGrid views={views} />);

describe("Today çalışma sırası", () => {
  it("plan eşlikçisini bağlamdan çıkarır ve planın yanında tek kez çizer", () => {
    const heatmap = view("activity.heatmap", "context");
    heatmap.widget.besidePlan = true;
    const html = page([view("plan", "plan"), heatmap, view("feed", "context")]);
    expect(html.split('data-today-widget="activity.heatmap"')).toHaveLength(2);
    expect(html.indexOf('data-today-widget="plan"')).toBeLessThan(html.indexOf('data-today-widget="activity.heatmap"'));
    expect(html.indexOf('data-today-widget="activity.heatmap"')).toBeLessThan(html.indexOf('aria-label="Bağlam"'));
  });
  it("bağlamı bağımsız anlamsal sütunlarda birer kez çizer; tanımsız yüzeyi ana sütunda tutar", () => {
    const views = ["today.career", "today.feed-stream", "learning.widget", "activity.heatmap", "optional"].map((id) => {
      const item = view(id, "context");
      if (id !== "optional")
        item.widget.contextLane = id === "today.feed-stream" || id === "activity.heatmap" ? "secondary" : "main";
      return item;
    });
    const html = page(views);
    const main = html.split('data-today-context-lane="main"')[1].split('data-today-context-lane="secondary"')[0];
    const secondary = html.split('data-today-context-lane="secondary"')[1];
    for (const id of ["today.career", "learning.widget", "optional"])
      expect(main).toContain(`data-today-widget="${id}"`);
    for (const id of ["today.feed-stream", "activity.heatmap"])
      expect(secondary).toContain(`data-today-widget="${id}"`);
    for (const item of views) expect(html.split(`data-today-widget="${item.id}"`)).toHaveLength(2);
  });
  it("girdideki modül sırası değişse de şimdi, iş, dikkat, bağlam DOM sırasını korur", () => {
    const html = page([
      view("akis", "context"),
      view("karar", "attention"),
      view("plan", "plan"),
      view("siradaki", undefined, "now"),
    ]);
    const positions = ["siradaki", "plan", "karar", "akis"].map((id) => html.indexOf(`data-today-widget="${id}"`));
    expect(positions).toEqual([...positions].sort((a, b) => a - b));
    expect(html).toContain('aria-label="Bugünün işi"');
    expect(html).toContain('aria-label="Dikkat isteyenler"');
    expect(html).toContain('aria-label="Bağlam"');
  });

  it("isteğe bağlı şimdi yüzeyi görünür listeden çıkarılırsa geri eklenmez", () => {
    const html = page([view("plan", "plan")]);
    expect(html).not.toContain('aria-label="Şimdi"');
    expect(html).toContain("empty:hidden");
    expect(html).toContain("lg:grid-cols-");
  });
});
