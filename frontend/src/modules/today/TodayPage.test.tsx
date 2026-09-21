import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { TodayPlacement } from "@/core/types";
import { HomeGrid } from "./TodayPage";
import type { TodayWidgetView } from "@/core/registry";

/**
 * Home iskelet yerleşimi (P2 §13/§14/§88).
 *
 * Sözleşme: ızgara TEK; masaüstünde üç kolon, dar ekranda tek kolon. Her
 * çekirdek yüzey `core` alanıyla kendi kolonuna yerleşir, DOM sırası ise
 * dar ekranda okuma sırasıdır (görsel sıra ile okuma sırası ayrışmaz).
 */

function view(id: string, core?: TodayPlacement): TodayWidgetView {
  const component = () => <span>{id}</span>;
  return { id, title: id, moduleId: "test", widget: { id, title: id, component, core, order: 1 } };
}

const page = (views: TodayWidgetView[]) => renderToStaticMarkup(<HomeGrid views={views} />);

describe("Home iskelet ızgarası", () => {
  it("dar ekranda tek kolon, masaüstünde üç kolon ve yoğun akış", () => {
    const html = page([view("a", "left")]);
    expect(html).toContain("grid-cols-1");
    expect(html).toContain("lg:grid-cols-[minmax(13rem,0.9fr)_minmax(0,1.5fr)_minmax(13rem,0.9fr)]");
    expect(html).toContain("lg:[grid-auto-flow:row_dense]");
  });

  it("çekirdek yüzeyler kolonlarına yerleşir", () => {
    const html = page([
      view("karar", "priority"),
      view("plan", "left"),
      view("akis", "center"),
      view("tarihler", "right"),
    ]);
    expect(html).toContain("lg:col-span-full");
    expect(html).toContain("lg:col-start-1");
    expect(html).toContain("lg:col-start-2");
    expect(html).toContain("lg:col-start-3");
  });

  it("isteğe bağlı yüzeyler kolon almaz: iskeletin altında akarlar", () => {
    const html = page([view("plan", "left"), view("ekstra")]);
    // Yalnız bir yerleşim sınıfı çizilir (çekirdeğinki).
    expect(html.match(/lg:col-start-\d/g)).toHaveLength(1);
  });

  it("DOM sırası verilen okuma sırasını korur", () => {
    const html = page([
      view("karar", "priority"),
      view("plan", "left"),
      view("tarihler", "right"),
      view("akis", "center"),
    ]);
    const order = ["karar", "plan", "tarihler", "akis"].map((label) => html.indexOf(label));
    expect(order).toEqual([...order].sort((a, b) => a - b));
  });

  it("kendini çizmeyen yüzey kolon yerini tutmaz", () => {
    const html = page([view("plan", "left")]);
    // Boş sarmalayıcı ızgaradan düşer: boş kart için delik açılmaz.
    expect(html).toContain("empty:hidden");
  });
});
