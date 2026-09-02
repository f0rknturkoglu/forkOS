// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { FeedItem } from "@/core/types";
import { RssReadingPane } from "./RssReadingPane";

const harness = vi.hoisted(() => ({ apiGet: vi.fn() }));
vi.mock("@/core/api", () => ({ api: { get: harness.apiGet } }));

const detail: FeedItem = {
  id: "item-1",
  feed_id: "feed-1",
  feed_title: "forkOS",
  title: "Güvenli içerik",
  url: "https://example.com",
  author: null,
  summary: null,
  content: '<p onclick="bad()">Merhaba</p><script>alert(1)</script>',
  published_at: "2026-08-23T10:00:00Z",
  fetched_at: "2026-08-23T10:01:00Z",
  read_at: null,
  saved_bookmark_id: null,
};

function paneProps(overrides: Partial<Parameters<typeof RssReadingPane>[0]> = {}) {
  return {
    detail,
    online: true,
    saveCollection: "read_later" as const,
    onSaveCollection: () => undefined,
    onToggleRead: () => undefined,
    onSave: () => undefined,
    onOpenBookmark: () => undefined,
    onPrev: () => undefined,
    onNext: () => undefined,
    hasPrev: false,
    hasNext: false,
    ...overrides,
  };
}

/** Mevcut sanitizer testlerinin SSR ciktisi (DOM'suz string kiyaslari). */
function ssr(content: string | null): string {
  return renderToStaticMarkup(<RssReadingPane {...paneProps({ detail: { ...detail, content } })} />);
}

describe("RSS reading pane", () => {
  it("renders article content while removing active HTML", () => {
    const html = ssr(detail.content);

    expect(html).toContain("Merhaba");
    expect(html).not.toContain("onclick");
    expect(html).not.toContain("script");
  });

  it("rejects javascript:/data: URL'leri, gecerli semalari korur", () => {
    const html = ssr(
      '<a href="javascript:alert(1)">kötü</a><a href="java&#x73;cript:alert(1)">kodlu</a>' +
        '<a href="mailto:bir@ornek.dev">posta</a><a href="https://ok.example/yazi">iyi</a>' +
        '<img src="data:image/svg+xml;base64,PHN2ZyBvbmxvYWQ9YWxlcnQoMSk+" alt="img">',
    );

    expect(html).not.toContain("javascript:");
    expect(html).not.toContain("data:");
    expect(html).toContain('href="https://ok.example/yazi"');
    expect(html).toContain('href="mailto:bir@ornek.dev"');
    expect(html).toContain("iyi");
    expect(html).toContain("kötü");
  });

  it("svg/math bloklarini komple kaldirir (onload dahil)", () => {
    const html = ssr('<svg onload="alert(1)"><a href="javascript:x">zararli</a></svg>');

    expect(html).not.toContain("onload");
    expect(html).not.toContain("zararli");
  });
});

describe("RSS tam metin", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
  });
  afterEach(() => cleanup());

  /** Ozet gorunumunde acilir: content yok, summary var, URL mevcut. */
  function renderPane() {
    return render(
      <RssReadingPane
        {...paneProps({ detail: { ...detail, content: null, summary: "Özet metni burada." } })}
      />,
    );
  }

  it("buton tıklanınca fetch çağrılır ve içerik tam metin modunda render edilir", async () => {
    harness.apiGet.mockResolvedValue({ full_text: "<p onclick='x()'>Fetch edilen tam metin</p>" });
    renderPane();

    fireEvent.click(screen.getByRole("button", { name: "Tam metni getir" }));

    expect(harness.apiGet).toHaveBeenCalledWith("/rss/items/item-1/fulltext");
    expect(await screen.findByText("Fetch edilen tam metin")).toBeTruthy();
    // Ozet/Tam metin toggle gorunur; icerik sanitarize edilir.
    expect(screen.getByRole("button", { name: "Özet" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Tam metin" })).toBeTruthy();
    expect(screen.queryByText("Özet metni burada.")).toBeNull();
    expect(screen.queryByText("onclick")).toBeNull();
  });

  it("null dönünce bilgi notu görünür, özet kalır", async () => {
    harness.apiGet.mockResolvedValue({ full_text: null });
    renderPane();

    fireEvent.click(screen.getByRole("button", { name: "Tam metni getir" }));

    expect(await screen.findByText("Tam metin alınamadı")).toBeTruthy();
    expect(screen.getByText("Özet metni burada.")).toBeTruthy();
  });

  it("fetch sürerken buton yükleniyor durumunda kilitlenir", async () => {
    let settle!: (value: { full_text: string | null }) => void;
    harness.apiGet.mockReturnValue(new Promise<{ full_text: string | null }>((resolve) => {
      settle = resolve;
    }));
    renderPane();

    fireEvent.click(screen.getByRole("button", { name: "Tam metni getir" }));
    const loading = screen.getByRole("button", { name: "Getiriliyor…" }) as HTMLButtonElement;
    expect(loading.disabled).toBe(true);

    settle({ full_text: null });
    await waitFor(() => expect(screen.queryByRole("button", { name: "Getiriliyor…" })).toBeNull());
    expect(screen.getByText("Tam metin alınamadı")).toBeTruthy();
  });

  it("toggle ile özet ve tam metin arasında geçiş yapılır", async () => {
    harness.apiGet.mockResolvedValue({ full_text: "<p>Uzun tam metin içeriği</p>" });
    renderPane();
    fireEvent.click(screen.getByRole("button", { name: "Tam metni getir" }));
    await screen.findByText("Uzun tam metin içeriği");

    fireEvent.click(screen.getByRole("button", { name: "Özet" }));
    expect(screen.getByText("Özet metni burada.")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Tam metin" }));
    expect(await screen.findByText("Uzun tam metin içeriği")).toBeTruthy();
  });
});
