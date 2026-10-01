// @vitest-environment jsdom
/**
 * Okuma Akışı sayfası (Polish 1 §8-§11/§35).
 *
 * Veri katmanı Home bileşeniyle AYNIdır (`core/feedStream`): burada sayfanın
 * kullanıcıya görünen davranışı sınanır — kaynak kimliği, filtre, kısmi hata ve
 * yeniden deneme.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { FeedPage } from "./FeedPage";

interface Call {
  path: string;
}

let calls: Call[] = [];
let failPaths: string[] = [];

vi.mock("@/app/router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/router")>();
  return { ...actual, navigate: vi.fn() };
});

const RSS_ITEM = {
  id: "r1",
  feed_id: "f1",
  feed_title: "Julia Blog",
  title: "RSS yazısı",
  published_at: "2026-09-20T08:00:00.000Z",
  fetched_at: "2026-09-20T08:05:00.000Z",
  read_at: null,
};

const REDDIT = {
  id: "t3_1",
  title: "Reddit gönderisi",
  url: "https://example.com/reddit",
  comments_url: "https://reddit.com/r/x/comments/1",
  subreddit: "programming",
  published_at: "2026-09-20T09:00:00.000Z",
};

const HN = {
  objectID: "42",
  title: "HN hikayesi",
  url: "https://example.com/hn",
  points: 120,
  num_comments: 30,
  created_at: "2026-09-20T10:00:00.000Z",
};

const REPO = {
  full_name: "owner/repo",
  html_url: "https://github.com/owner/repo",
  description: "açıklama",
  stargazers_count: 900,
  language: "TypeScript",
  created_at: "2026-09-20T11:00:00.000Z",
};

function bodyFor(path: string): unknown {
  if (path.startsWith("/rss/items")) return [RSS_ITEM];
  if (path.startsWith("/rss/stats")) return { unread: 7, feeds: 3, broken: 0 };
  if (path.startsWith("/news/reddit")) return [REDDIT];
  if (path.startsWith("/news/hacker-news")) return [HN];
  if (path.startsWith("/news/github-trending")) return [REPO];
  return [];
}

beforeEach(() => {
  calls = [];
  failPaths = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      const path = url.pathname.replace(/^\/api/, "") + url.search;
      calls.push({ path });
      if (failPaths.some((prefix) => path.startsWith(prefix))) {
        return new Response(JSON.stringify({ detail: "kaynak alınamadı" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify(bodyFor(path)), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
});

afterEach(cleanup);

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <FeedPage />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("Okuma Akışı sayfası", () => {
  it("F1/F9: akış sayfası dört kaynağı tek listede toplar", async () => {
    renderPage();

    expect(await screen.findByText("RSS yazısı")).toBeTruthy();
    expect(screen.getByText("Reddit gönderisi")).toBeTruthy();
    expect(screen.getByText("HN hikayesi")).toBeTruthy();
    expect(screen.getByText("owner/repo")).toBeTruthy();

    // Aynı veri katmanı: Home widget'ının kullandığı uçlar.
    const paths = calls.map((call) => call.path);
    for (const prefix of ["/rss/items", "/news/reddit", "/news/hacker-news", "/news/github-trending"]) {
      expect(paths.some((path) => path.startsWith(prefix))).toBe(true);
    }
  });

  it("kaynak kimliği açıkça görünür ve RSS dışı bağlantılar yeni sekmede açılır", async () => {
    renderPage();

    // Kaynak rozeti başlıkta da (legend) satırda da görünür: en az iki kez.
    await screen.findByText("HN hikayesi");
    expect(screen.getAllByText("Hacker News").length).toBeGreaterThanOrEqual(2);
    const external = screen.getByRole("link", { name: "HN hikayesi" });
    expect(external.getAttribute("target")).toBe("_blank");
    // RSS satırı yerel okuyucuya gider (dış bağlantı değil).
    expect(screen.queryByRole("link", { name: "RSS yazısı" })).toBeNull();
    expect(screen.getByRole("button", { name: "RSS yazısı" })).toBeTruthy();
  });

  it("F6: kaynak filtresi listeyi daraltır", async () => {
    renderPage();

    await screen.findByText("RSS yazısı");
    fireEvent.click(screen.getByRole("tab", { name: "GitHub" }));

    await waitFor(() => expect(screen.getByText("owner/repo")).toBeTruthy());
    expect(screen.queryByText("RSS yazısı")).toBeNull();
    expect(screen.queryByText("HN hikayesi")).toBeNull();
  });

  it("F7: kısmi kaynak hatası listede kalanı gösterir ve kaynağı işaretler", async () => {
    failPaths = ["/news/hacker-news"];
    renderPage();

    expect(await screen.findByText("RSS yazısı")).toBeTruthy();
    expect(await screen.findByText(/Hacker News alınamadı/, {}, { timeout: 4000 })).toBeTruthy();
    // Ekran çökmedi: diğer kaynaklar yerinde.
    expect(screen.getByText("owner/repo")).toBeTruthy();
  });

  it("F8: yeniden dene düğmesi başarısız kaynağı tekrar ister", async () => {
    failPaths = ["/news/reddit"];
    renderPage();

    const retry = await screen.findByRole("button", { name: "Reddit'i yeniden dene" }, { timeout: 4000 });
    const before = calls.filter((call) => call.path.startsWith("/news/reddit")).length;
    failPaths = [];
    fireEvent.click(retry);

    await waitFor(() =>
      expect(calls.filter((call) => call.path.startsWith("/news/reddit")).length).toBeGreaterThan(before),
    );
    expect(await screen.findByText("Reddit gönderisi")).toBeTruthy();
  });

  it("tüm kaynaklar boşsa dürüst boş durum gösterir", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), "http://localhost");
        const path = url.pathname.replace(/^\/api/, "") + url.search;
        calls.push({ path });
        return new Response(JSON.stringify(path.startsWith("/rss/stats") ? { unread: 0 } : []), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
    renderPage();

    expect(await screen.findByText("Bu kaynakta yeni bir şey yok.")).toBeTruthy();
  });

  it("okunmamış RSS sayısı başlıkta görünür", async () => {
    renderPage();
    expect(await screen.findByText("7 okunmamış RSS yazısı")).toBeTruthy();
  });

  it("F10: akış mantığı ikinci kez yazılmadı — sayfa ortak veri katmanını kullanır", async () => {
    renderPage();
    await screen.findByText("RSS yazısı");

    // Kaynak başına sorgu TEK kez: /news uçları iki kez istenmez.
    const redditCalls = calls.filter((call) => call.path.startsWith("/news/reddit"));
    expect(redditCalls.length).toBe(1);
    const rssCalls = calls.filter((call) => call.path.startsWith("/rss/items"));
    expect(rssCalls.length).toBe(1);
    expect(within(document.body).getAllByText("HN hikayesi").length).toBe(1);
  });
});
