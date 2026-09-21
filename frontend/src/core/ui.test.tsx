// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CopyButton, Metric, MetricStrip, PageFrame, RowList, Section, Surface, ToastProvider, Toolbar } from "./ui";

/** Pano erişilemediğinde kullanıcıya gösterilen tek cümle (ham hata metni değil). */
const CLIPBOARD_WARNING = "Pano erişilemedi — tarayıcı izni gerekiyor.";

/** Pano API'sini test başına takar; `undefined` vermek API'nin yokluğunu taklit eder. */
function stubClipboard(writeText: ((text: string) => Promise<void>) | undefined) {
  Object.defineProperty(navigator, "clipboard", {
    value: writeText ? { writeText } : undefined,
    configurable: true,
    writable: true,
  });
}

function renderCopy(text: string, props: { disabled?: boolean; ariaLabel?: string } = {}) {
  return render(
    <ToastProvider>
      <CopyButton text={text} {...props} />
    </ToastProvider>,
  );
}

afterEach(() => {
  cleanup();
  stubClipboard(undefined);
});

describe("UI primitives", () => {
  it("wraps section content in a card shell by default", () => {
    const html = renderToStaticMarkup(
      <Section title="RSS">
        <p>Akış</p>
      </Section>,
    );

    expect(html).toContain("RSS");
    expect(html).toContain("Akış");
    expect(html).toContain("rounded-card border border-subtle bg-surface");
  });

  it("drops the shell when nested inside another surface", () => {
    const html = renderToStaticMarkup(
      <Section title="RSS" flat>
        <p>Akış</p>
      </Section>,
    );

    expect(html).not.toContain("rounded-card border border-subtle bg-surface");
  });

  it("keeps explicit surfaces, metrics, toolbars, and divided rows", () => {
    const html = renderToStaticMarkup(
      <PageFrame>
        <Surface>
          <Toolbar>Filtre</Toolbar>
        </Surface>
        <MetricStrip>
          <Metric label="Açık" value={12} />
        </MetricStrip>
        <RowList>Satır</RowList>
      </PageFrame>,
    );

    expect(html).toContain("max-w-[1600px]");
    expect(html).toContain("divide-x");
    expect(html).toContain("divide-y");
  });

  it("can keep semantic list markup while using divided-row styling", () => {
    const html = renderToStaticMarkup(
      <RowList as="ul">
        <li>Birinci</li>
      </RowList>,
    );

    expect(html).toContain("<ul");
    expect(html).toContain("<li>Birinci</li>");
  });
});

describe("CopyButton", () => {
  it("metni panoya yazar, bildirim verir ve düğmede kopyalandı durumunu gösterir", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    stubClipboard(writeText);
    renderCopy("taşınmış not gövdesi");

    fireEvent.click(screen.getByRole("button", { name: "Kopyala" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledWith("taşınmış not gövdesi"));
    // Bildirim tam noktalı cümledir; düğmenin kendi etiketi noktasızdır.
    expect(await screen.findByText("Kopyalandı.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Kopyala" }).textContent).toContain("Kopyalandı");
  });

  it("pano API'si yoksa sessizce uyarır, ham hata sızdırmaz", async () => {
    stubClipboard(undefined);
    renderCopy("metin");

    expect(() => fireEvent.click(screen.getByRole("button", { name: "Kopyala" }))).not.toThrow();

    expect(await screen.findByText(CLIPBOARD_WARNING)).toBeTruthy();
    // Başarısız kopyalama "kopyalandı" durumuna geçmez.
    expect(screen.getByRole("button", { name: "Kopyala" }).textContent).not.toContain("Kopyalandı");
  });

  it("izin reddinde istisna metnini değil sınırlı uyarıyı gösterir", async () => {
    stubClipboard(() => Promise.reject(new Error("NotAllowedError: Write permission denied")));
    renderCopy("metin");

    fireEvent.click(screen.getByRole("button", { name: "Kopyala" }));

    expect(await screen.findByText(CLIPBOARD_WARNING)).toBeTruthy();
    expect(document.body.textContent).not.toContain("NotAllowedError");
    expect(document.body.textContent).not.toContain("permission denied");
  });

  it("kopyalandı durumu kendiliğinden geri döner", async () => {
    vi.useFakeTimers();
    try {
      stubClipboard(vi.fn().mockResolvedValue(undefined));
      renderCopy("metin");
      const button = screen.getByRole("button", { name: "Kopyala" });

      fireEvent.click(button);
      await act(async () => {});
      expect(button.textContent).toBe("Kopyalandı");

      await act(async () => vi.advanceTimersByTime(1600));
      expect(button.textContent).toBe("Kopyala");
    } finally {
      vi.useRealTimers();
    }
  });

  it("boş metinde kapanır", () => {
    stubClipboard(vi.fn().mockResolvedValue(undefined));
    renderCopy("");

    expect(screen.getByRole("button", { name: "Kopyala" }).hasAttribute("disabled")).toBe(true);
  });

  it("disabled verildiğinde kapanır ve ariaLabel erişilebilir ad olur", () => {
    stubClipboard(vi.fn().mockResolvedValue(undefined));
    renderCopy("metin", { disabled: true, ariaLabel: "Gövdeyi kopyala" });

    expect(screen.getByRole("button", { name: "Gövdeyi kopyala" }).hasAttribute("disabled")).toBe(true);
  });
});
