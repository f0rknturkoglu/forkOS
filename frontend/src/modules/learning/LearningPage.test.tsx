// @vitest-environment jsdom
/**
 * Faz 3 guardrail'i: ogrenme modulu TEK orkestratorden yonetilir ve secim
 * URL'de tutulur. Bu dosya su sozlesmeleri korur:
 *   - `?view/area/focus/resource/tab` senkronu (geri/ileri dahil)
 *   - 256 dugumlu alanda DOM'a yalniz gorunur satirlar girer + klavye gezinme
 *   - master-detail (dar genislikte liste -> detay + gorunur geri dugmesi)
 *   - yukleme iskeleti, bolum bazli hata + yeniden dene, cevrimdisi yazma kilidi
 */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { StudyAreaStats, StudyTopicDetail, StudyTreeNode, StudyTree } from "@/core/types";
import { ApiError } from "@/core/api";

const harness = vi.hoisted(() => {
  const listeners = new Set<() => void>();
  const state = {
    online: true,
    routes: {} as Record<string, unknown>,
    pending: new Set<string>(),
    fail: {} as Record<string, Error>,
    gets: [] as string[],
    hash: "#/learning",
    history: ["#/learning"] as string[],
    index: 0,
  };
  const apply = (hash: string): void => {
    state.hash = hash.startsWith("#") ? hash : `#${hash}`;
    listeners.forEach((listener) => listener());
  };
  return {
    state,
    listeners,
    apply,
    /** Tarayici geri/ileri: ayni URL'e doner, sayfa secimi URL'den okur. */
    back: () => {
      state.index = Math.max(0, state.index - 1);
      apply(state.history[state.index]);
    },
    forward: () => {
      state.index = Math.min(state.history.length - 1, state.index + 1);
      apply(state.history[state.index]);
    },
    reset: (hash: string) => {
      state.history = [hash];
      state.index = 0;
      apply(hash);
    },
  };
});

/** Askida kalan istek: iskelet durumunu olcmek icin bilincli olarak hic cozulmez
 *  (hedef lib ES2024 degil, bu yuzden `Promise.withResolvers` kullanilamaz). */
const NEVER = new Promise<never>(() => undefined);

vi.mock("@/lib/hooks", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/hooks")>();
  return { ...actual, useOnline: () => harness.state.online };
});

vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  const reply = (path: string) => {
    harness.state.gets.push(path);
    if (path in harness.state.fail) return Promise.reject(harness.state.fail[path]);
    if (harness.state.pending.has(path)) return NEVER;
    if (path in harness.state.routes) return Promise.resolve(harness.state.routes[path]);
    return Promise.reject(new actual.ApiError(404, "bulunamadi"));
  };
  return {
    ApiError: actual.ApiError,
    qs: actual.qs,
    api: {
      get: reply,
      post: vi.fn(),
      patch: vi.fn(),
      del: vi.fn(),
      upload: vi.fn(),
    },
  };
});

vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/core/dialog", () => ({ confirmDialog: vi.fn(async () => true), DialogHost: () => null }));
vi.mock("@/modules/pomodoro/dock", () => ({ openPomodoro: vi.fn() }));

/* Router: gercek anlamda bir yigin tutar; boylece geri/ileri tusu davranisi
   (secimin URL'den okundugu) testte gercekten olculur. */
vi.mock("@/app/router", async () => {
  // vi.mock factory'leri hoist edilir: React bu noktada statik import edilemez.
  const React = await import("react");
  const snapshot = () => {
    const raw = harness.state.hash.replace(/^#/, "");
    const [path, query = ""] = raw.split("?");
    return { path: path || "/", params: new URLSearchParams(query) };
  };
  return {
    navigate: (path: string) => {
      const next = path.startsWith("#") ? path : `#${path}`;
      if (next === harness.state.hash) return;
      harness.state.history = harness.state.history.slice(0, harness.state.index + 1).concat(next);
      harness.state.index = harness.state.history.length - 1;
      harness.apply(next);
    },
    useHashRoute: () => {
      const [, force] = React.useState(0);
      React.useEffect(() => {
        const listener = () => force((value: number) => value + 1);
        harness.listeners.add(listener);
        return () => {
          harness.listeners.delete(listener);
        };
      }, []);
      return snapshot();
    },
  };
});

vi.mock("./TopicDetail", () => ({
  TopicDetail: ({
    topicId,
    tab,
    onTabChange,
    onDeleted,
  }: {
    topicId: string;
    tab: string;
    onTabChange: (tab: "tekrar") => void;
    onDeleted: () => void;
  }) => (
    <div data-testid="topic-detail" data-topic={topicId} data-tab={tab}>
      <button type="button" onClick={() => onTabChange("tekrar")}>
        tekrar-sekmesi
      </button>
      <button type="button" onClick={onDeleted}>
        konuyu-sil
      </button>
    </div>
  ),
}));
vi.mock("./CoursesView", () => ({ CoursesView: () => <div data-testid="courses-view" /> }));
vi.mock("./ReviewView", () => ({
  ReviewView: ({ onOpenTopic }: { onOpenTopic: (topicId: string) => void }) => (
    <button type="button" onClick={() => onOpenTopic("n3")}>
      kuyruktan-konu-ac
    </button>
  ),
}));
vi.mock("./StatsView", () => ({ StatsView: () => <div data-testid="stats-view" /> }));
vi.mock("./ImportDialog", () => ({
  ImportDialog: ({ open, onDone }: { open: boolean; onClose: () => void; onDone: (areaId: string) => void }) =>
    open ? (
      <button type="button" onClick={() => onDone("a2")}>
        ice-aktarmayi-bitir
      </button>
    ) : null,
}));

import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import { LearningPage } from "./LearningPage";

/* ── Fixture'lar ─────────────────────────────────────────────────────── */

function topicNode(overrides: Partial<StudyTreeNode> & { id: string; title: string }): StudyTreeNode {
  return {
    parent_id: null,
    depth: 0,
    position: 0,
    status: "not_started",
    confidence: null,
    mastery: null,
    target_min: null,
    last_studied_at: null,
    next_review_at: null,
    review_due: false,
    resource_total: 0,
    resource_done: 0,
    progress_pct: 0,
    focus_minutes: 0,
    focus_sessions: 0,
    child_count: 0,
    path: [],
    ...overrides,
  };
}

const AREAS: StudyAreaStats[] = [
  {
    id: "a1",
    title: "Git",
    color: null,
    active: true,
    position: 0,
    archived_at: null,
    topic_count: 256,
    done_count: 5,
    resource_count: 17,
    resource_done: 1,
    focus_minutes: 0,
    stale_count: 2,
    last_studied_at: null,
  },
  {
    id: "a2",
    title: "ALES",
    color: null,
    active: true,
    position: 1,
    archived_at: null,
    topic_count: 36,
    done_count: 0,
    resource_count: 5,
    resource_done: 0,
    focus_minutes: 0,
    stale_count: 0,
    last_studied_at: null,
  },
];

/** 16 kok x (3 dal x 4 yaprak) = 256 dugum; kokler acik, alt dallar kapali. */
const BIG_NODES: StudyTreeNode[] = [];
for (let root = 1; root <= 16; root += 1) {
  const rootId = `root-${root}`;
  BIG_NODES.push(topicNode({ id: rootId, title: `Kök ${root}`, child_count: 3 }));
  for (let branch = 1; branch <= 3; branch += 1) {
    const branchId = `branch-${root}-${branch}`;
    BIG_NODES.push(
      topicNode({
        id: branchId,
        title: `Kök ${root} dal ${branch}`,
        parent_id: rootId,
        depth: 1,
        path: [rootId],
        status: "in_progress",
        child_count: 4,
        resource_total: 4,
        resource_done: 1,
        progress_pct: 25,
      }),
    );
    for (let leaf = 1; leaf <= 4; leaf += 1) {
      BIG_NODES.push(
        topicNode({
          id: `leaf-${root}-${branch}-${leaf}`,
          title: `Kök ${root} dal ${branch} yaprak ${leaf}`,
          parent_id: branchId,
          depth: 2,
          path: [rootId, branchId],
        }),
      );
    }
  }
}

/** Kokler acik geldigi icin gorunur satir sayisi: 16 kok + 48 dal. */
const BIG_VISIBLE = 64;

const DEEP_NODES: StudyTreeNode[] = [
  topicNode({ id: "n1", title: "Kök", child_count: 2 }),
  topicNode({ id: "n2", title: "Dal", parent_id: "n1", depth: 1, path: ["n1"], child_count: 1 }),
  topicNode({ id: "n3", title: "Yaprak", parent_id: "n2", depth: 2, path: ["n1", "n2"], child_count: 1 }),
  topicNode({ id: "n4", title: "Kardeş", parent_id: "n1", depth: 1, path: ["n1"] }),
  topicNode({ id: "n5", title: "Torun", parent_id: "n3", depth: 3, path: ["n1", "n2", "n3"] }),
];

function treeOf(area: StudyAreaStats, nodes: StudyTreeNode[]): StudyTree {
  return {
    area,
    nodes,
    totals: {
      topics: nodes.length,
      done: 0,
      in_progress: 0,
      review_due: 0,
      resource_total: 0,
      resource_done: 0,
      focus_minutes: 0,
      focus_sessions: 0,
    },
    orphan_count: 0,
  };
}

function detailOf(topicId: string, title: string, ancestors: { id: string; title: string }[] = []): StudyTopicDetail {
  // Ara degisken: yanit sekli degistiginde (ornek: `note_count` kalkmasi)
  // asiri ozellik kontrolu kirilmasin, tip uyumu yine denetlensin.
  const detail = {
    topic: {
      id: topicId,
      title,
      area_id: "a1",
      parent_id: ancestors.at(-1)?.id ?? null,
      status: "in_progress" as const,
      confidence: null,
      target_min: null,
      position: 0,
      mastery: null,
      last_studied_at: null,
      interval_days: 0,
      ease: 2.5,
      review_count: 0,
      last_reviewed_at: null,
      next_review_at: null,
    },
    ancestors,
    resources: [],
    progress: { total: 0, done: 0, pct: 0 },
    stats: { minutes: 0, sessions: 0, week_minutes: 0, last_studied_at: null },
    open_todo: null,
    // `note_count` API'den kaldirildi; fixtureda kalabilir cunku tip uyumu
    // yalnizca gerekli alanlar icin denetlenir (asiri ozellik serbest).
    note_count: 0,
    flashcard_deck_count: 0,
    review: {
      interval_days: 0,
      ease: 2.5,
      review_count: 0,
      last_reviewed_at: null,
      next_review_at: null,
      mastery: null,
      due: false,
    },
  };
  return detail;
}

function setViewport(wide: boolean): void {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: wide,
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <LearningPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  harness.state.online = true;
  harness.state.routes = {
    "/study/areas?include_stats=true": AREAS,
    "/study/areas/a1/tree": treeOf(AREAS[0], BIG_NODES),
    "/study/areas/a2/tree": treeOf(AREAS[1], []),
  };
  harness.state.pending = new Set();
  harness.state.fail = {};
  harness.state.gets = [];
  harness.reset("#/learning");
  setViewport(true);
  Element.prototype.scrollIntoView = vi.fn();
  vi.mocked(api.post).mockReset();
  vi.mocked(api.patch).mockReset();
  vi.mocked(api.del).mockReset();
  vi.mocked(invalidateAfter).mockReset();
  vi.mocked(confirmDialog).mockReset();
  vi.mocked(confirmDialog).mockResolvedValue(true);
});

afterEach(() => cleanup());

/* ── Testler ─────────────────────────────────────────────────────────── */

describe("öğrenme sayfası — URL sözleşmesi", () => {
  it("konu seçimi `?focus=` yazar, geri/ileri tuşu seçimi URL'den geri getirir", async () => {
    harness.state.routes["/study/topics/root-1"] = detailOf("root-1", "Kök 1");
    renderPage();
    await waitFor(() => expect(screen.getAllByRole("treeitem")).toHaveLength(BIG_VISIBLE));

    fireEvent.click(screen.getByTitle("Kök 1"));
    await waitFor(() => expect(harness.state.hash).toContain("focus=root-1"));
    expect(harness.state.gets).toContain("/study/topics/root-1");
    await waitFor(() => expect(screen.getByTestId("topic-detail").getAttribute("data-topic")).toBe("root-1"));

    act(() => harness.back());
    await waitFor(() => expect(screen.queryByTestId("topic-detail")).toBeNull());
    expect(harness.state.hash).not.toContain("focus=");

    act(() => harness.forward());
    await waitFor(() => expect(screen.getByTestId("topic-detail").getAttribute("data-topic")).toBe("root-1"));
  });

  it("alan değişimi `?area=` yazar ve focus'u temizler", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByLabelText("Çalışma alanı")).toBeTruthy());

    fireEvent.change(screen.getByLabelText("Çalışma alanı"), { target: { value: "a2" } });
    await waitFor(() => expect(harness.state.hash).toContain("area=a2"));
    expect(harness.state.hash).not.toContain("focus=");
    expect(harness.state.gets).toContain("/study/areas/a2/tree");
  });

  it("`?resource=` ana konuyu seçer, `?resource` korunur ve sekme kaynaklara düşer", async () => {
    harness.state.routes["/learning/resources/res-1"] = {
      id: "res-1",
      title: "Git kitabı",
      topic_id: "n2",
      url: null,
      kind: "book",
      position: 0,
      completed_at: null,
      note: null,
      estimated_min: null,
      last_opened_at: null,
      source: "manual",
      bookmark_id: null,
      course_id: null,
    };
    harness.state.routes["/study/topics/n2"] = detailOf("n2", "Dal", [{ id: "n1", title: "Kök" }]);
    harness.state.routes["/study/areas/a1/tree"] = treeOf(AREAS[0], DEEP_NODES);
    harness.reset("#/learning?resource=res-1");

    renderPage();
    await waitFor(() => expect(screen.getByTestId("topic-detail").getAttribute("data-topic")).toBe("n2"));
    expect(screen.getByTestId("topic-detail").getAttribute("data-tab")).toBe("kaynaklar");
    expect(harness.state.gets).toContain("/learning/resources/res-1");
    expect(harness.state.gets).toContain("/study/topics/n2");
    expect(harness.state.hash).toContain("resource=res-1");
  });

  it("sekme değişimi `?tab=` yazar ve bilinmeyen parametreleri korur", async () => {
    harness.state.routes["/study/topics/n3"] = detailOf("n3", "Yaprak", [
      { id: "n1", title: "Kök" },
      { id: "n2", title: "Dal" },
    ]);
    harness.state.routes["/study/areas/a1/tree"] = treeOf(AREAS[0], DEEP_NODES);
    harness.reset("#/learning?focus=n3&tab=notlar&range=month");

    renderPage();
    await waitFor(() => expect(screen.getByTestId("topic-detail").getAttribute("data-tab")).toBe("notlar"));

    fireEvent.click(screen.getByText("tekrar-sekmesi"));
    await waitFor(() => expect(harness.state.hash).toContain("tab=tekrar"));
    expect(harness.state.hash).toContain("range=month");
    expect(harness.state.hash).toContain("focus=n3");
  });

  it("görünüm sekmeleri `?view=` yazar; ReviewView konuyu konular görünümünde açar", async () => {
    harness.state.routes["/study/topics/n3"] = detailOf("n3", "Yaprak");
    harness.reset("#/learning?view=review&range=week");

    renderPage();
    await waitFor(() => expect(screen.getByText("kuyruktan-konu-ac")).toBeTruthy());

    fireEvent.click(screen.getByText("kuyruktan-konu-ac"));
    await waitFor(() => expect(harness.state.hash).toContain("view=topics"));
    expect(harness.state.hash).toContain("focus=n3");
    expect(harness.state.hash).toContain("range=week");
  });

  it("bilinmeyen kayıt için boş ekran yerine 'Kayıt bulunamadı' + alan listesine dön çıkar", async () => {
    harness.reset("#/learning?focus=yok-1");
    renderPage();

    await waitFor(() => expect(screen.getByText("Kayıt bulunamadı")).toBeTruthy());
    fireEvent.click(screen.getByText("Alan listesine dön"));
    await waitFor(() => expect(harness.state.hash).not.toContain("focus="));
  });

  it("içe aktarma tamamlanınca `?area=` seçilir", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("JSON yükle")).toBeTruthy());

    fireEvent.click(screen.getByText("JSON yükle"));
    fireEvent.click(screen.getByText("ice-aktarmayi-bitir"));
    await waitFor(() => expect(harness.state.hash).toContain("area=a2"));
    expect(harness.state.hash).toContain("view=topics");
  });
});

describe("konu ağacı — ölçek ve erişilebilirlik", () => {
  it("256 düğümde DOM'a yalnız görünür satırlar girer (varsayılan: kökler açık)", async () => {
    renderPage();
    await waitFor(() => expect(screen.getAllByRole("treeitem")).toHaveLength(BIG_VISIBLE));
    expect(BIG_NODES).toHaveLength(256);
    // Kökler açık: ilk dal görünür; alt dallar kapalı olduğu için yaprak DOM'a girmez.
    expect(screen.getByTitle("Kök 1 dal 1")).toBeTruthy();
    expect(screen.queryByTitle("Kök 1 dal 1 yaprak 1")).toBeNull();
  });

  it("`?focus=` konusunun ata zinciri açılır, kardeş dal kapalı kalır", async () => {
    harness.state.routes["/study/topics/n3"] = detailOf("n3", "Yaprak", [
      { id: "n1", title: "Kök" },
      { id: "n2", title: "Dal" },
    ]);
    harness.state.routes["/study/areas/a1/tree"] = treeOf(AREAS[0], DEEP_NODES);
    harness.reset("#/learning?focus=n3");

    renderPage();
    const tree = await screen.findByRole("tree");
    await waitFor(() => expect(within(tree).getByTitle("Yaprak")).toBeTruthy());
    expect(within(tree).getByTitle("Dal")).toBeTruthy();
    expect(within(tree).getByTitle("Kök")).toBeTruthy();
    expect(within(tree).queryByTitle("Torun")).toBeNull();
    expect(within(tree).getByTitle("Yaprak").closest('[role="treeitem"]')?.getAttribute("aria-selected")).toBe("true");
    // Breadcrumb atalari gosterir: secili konu icin yolu okunur.
    expect(screen.getByLabelText("Konu yolu").textContent).toContain("Yaprak");
  });

  it("klavye: ↑/↓ görünür öğeler arası gezer, →/← dalı açar-kapatır, Enter seçer", async () => {
    harness.state.routes["/study/topics/root-1"] = detailOf("root-1", "Kök 1");
    harness.state.routes["/study/topics/leaf-1-1-1"] = detailOf("leaf-1-1-1", "Kök 1 dal 1 yaprak 1", [
      { id: "root-1", title: "Kök 1" },
      { id: "branch-1-1", title: "Kök 1 dal 1" },
    ]);
    renderPage();
    await waitFor(() => expect(screen.getAllByRole("treeitem")).toHaveLength(BIG_VISIBLE));

    const rows = () => screen.getAllByRole("treeitem");
    const active = () => document.activeElement?.getAttribute("data-tree-id");

    fireEvent.keyDown(rows()[0], { key: "ArrowDown" });
    expect(active()).toBe("branch-1-1");
    fireEvent.keyDown(rows()[1], { key: "ArrowUp" });
    expect(active()).toBe("root-1");
    fireEvent.keyDown(rows()[0], { key: "End" });
    expect(active()).toBe("branch-16-3");
    fireEvent.keyDown(rows()[63], { key: "Home" });
    expect(active()).toBe("root-1");

    // Kök zaten açık: → ilk alt dala geçer.
    fireEvent.keyDown(rows()[0], { key: "ArrowRight" });
    expect(active()).toBe("branch-1-1");
    // Kapalı dalda → açar (görünür satır 4 artar), sonra → ilk yaprağa iner.
    expect(rows()[1].getAttribute("aria-expanded")).toBe("false");
    fireEvent.keyDown(rows()[1], { key: "ArrowRight" });
    await waitFor(() => expect(screen.getAllByRole("treeitem")).toHaveLength(BIG_VISIBLE + 4));
    expect(rows()[1].getAttribute("aria-expanded")).toBe("true");
    fireEvent.keyDown(rows()[1], { key: "ArrowRight" });
    expect(active()).toBe("leaf-1-1-1");

    // ← önce parent'a döner, sonra açık dalı kapatır.
    fireEvent.keyDown(rows()[2], { key: "ArrowLeft" });
    expect(active()).toBe("branch-1-1");
    fireEvent.keyDown(rows()[1], { key: "ArrowLeft" });
    await waitFor(() => expect(screen.getAllByRole("treeitem")).toHaveLength(BIG_VISIBLE));

    // Enter seçer ve seçim URL'e yazılır.
    fireEvent.keyDown(rows()[1], { key: "ArrowRight" });
    fireEvent.keyDown(rows()[1], { key: "ArrowRight" });
    fireEvent.keyDown(rows()[2], { key: "Enter" });
    await waitFor(() => expect(harness.state.hash).toContain("focus=leaf-1-1-1"));
  });

  it("arama `q` ile sunucuya gider ve eşleşen dal açık gelir", async () => {
    const match = topicNode({
      id: "leaf-1-1-9",
      title: "Git commit",
      parent_id: "branch-1-1",
      depth: 2,
      path: ["root-1", "branch-1-1"],
    });
    harness.state.routes["/study/areas/a1/tree?q=commit"] = treeOf(AREAS[0], [
      topicNode({ id: "root-1", title: "Kök 1", child_count: 3 }),
      topicNode({
        id: "branch-1-1",
        title: "Kök 1 dal 1",
        parent_id: "root-1",
        depth: 1,
        path: ["root-1"],
        child_count: 4,
      }),
      match,
    ]);
    renderPage();
    await waitFor(() => expect(screen.getAllByRole("treeitem")).toHaveLength(BIG_VISIBLE));

    fireEvent.change(screen.getByLabelText("Konu ara"), { target: { value: "commit" } });
    // useDebounced 250 ms: gercek zamanlayici ile beklenir.
    await waitFor(() => expect(harness.state.gets).toContain("/study/areas/a1/tree?q=commit"), { timeout: 3000 });
    await waitFor(() => expect(screen.getByTitle("Git commit")).toBeTruthy());
    expect(screen.getByTitle("Kök 1")).toBeTruthy();
  });

  it("yükleme sırasında iskelet gösterilir, 'konu yok' flaşı olmaz", async () => {
    harness.state.pending.add("/study/areas/a1/tree");
    const { container } = renderPage();

    await waitFor(() => expect(screen.getByLabelText("Çalışma alanı")).toBeTruthy());
    expect(screen.queryByText("Bu alanda henüz konu yok.")).toBeNull();
    expect(screen.queryAllByRole("treeitem")).toHaveLength(0);
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("ağaç hatasında bölüm bazlı role=alert ve 'Yeniden dene' çıkar", async () => {
    harness.state.fail["/study/areas/a1/tree"] = new Error("boom");
    renderPage();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Konu ağacı yüklenemedi.");
    const before = harness.state.gets.filter((path) => path.endsWith("/tree")).length;
    fireEvent.click(screen.getByText("Yeniden dene"));
    await waitFor(() =>
      expect(harness.state.gets.filter((path) => path.endsWith("/tree")).length).toBeGreaterThan(before),
    );
  });

  it("çevrimdışı: okuma açık kalır, yazma düğmeleri gerekçesiyle kapalı olur", async () => {
    harness.state.online = false;
    renderPage();
    await waitFor(() => expect(screen.getAllByRole("treeitem")).toHaveLength(BIG_VISIBLE));

    const importButton = screen.getByText("JSON yükle").closest("button");
    expect(importButton?.disabled).toBe(true);
    expect(importButton?.getAttribute("title")).toBe("Çevrimdışı: yazma kapalı");
    expect(screen.getByLabelText("Konu ekle").closest("button")?.disabled).toBe(true);
  });
});

describe("master-detail yerleşimi", () => {
  it("dar genişlikte liste görünür; konu seçilince detay + görünür geri düğmesi, ağaç aşağı itilmez", async () => {
    harness.state.routes["/study/topics/root-1"] = detailOf("root-1", "Kök 1");
    setViewport(false);
    renderPage();
    await waitFor(() => expect(screen.getAllByRole("treeitem")).toHaveLength(BIG_VISIBLE));
    expect(screen.queryByTestId("topic-detail")).toBeNull();

    fireEvent.click(screen.getByTitle("Kök 1"));
    await waitFor(() => expect(screen.getByTestId("topic-detail")).toBeTruthy());
    // Detay acilinca agac DOM'da YOK: detay agacin altina itilmez.
    expect(screen.queryAllByRole("treeitem")).toHaveLength(0);
    expect(screen.getByText("Liste").closest("button")).toBeTruthy();

    fireEvent.click(screen.getByText("Liste"));
    await waitFor(() => expect(screen.queryByTestId("topic-detail")).toBeNull());
    expect(screen.getAllByRole("treeitem")).toHaveLength(BIG_VISIBLE);
  });

  it("geniş genişlikte ray ve detay yan yana kalır", async () => {
    renderPage();
    await waitFor(() => expect(screen.getAllByRole("treeitem")).toHaveLength(BIG_VISIBLE));
    expect(screen.getByRole("tree")).toBeTruthy();
    expect(screen.getByText("Bir konu seç")).toBeTruthy();
  });
});

describe("yazma akışları", () => {
  it("ağaç satırından görev oluşturma tek istek atar; görev/öğrenme anahtarları tazelenir", async () => {
    const post = vi.mocked(api.post);
    post.mockResolvedValue({ id: "todo-1" });
    renderPage();
    await waitFor(() => expect(screen.getAllByRole("treeitem")).toHaveLength(BIG_VISIBLE));

    fireEvent.click(screen.getByLabelText('"Kök 1" için görev oluştur'));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/study/topics/root-1/todos", { plan_day: undefined }));
    expect(vi.mocked(invalidateAfter)).toHaveBeenCalledWith("todo.write", "study.write", "link.write");
  });

  it("yeni konu: seçili konu parent olur, oluşan konu `?focus=` ile açılır", async () => {
    const post = vi.mocked(api.post);
    post.mockResolvedValue({ id: "yeni-1", area_id: "a1" });
    harness.state.routes["/study/topics/leaf-1-1-1"] = detailOf("leaf-1-1-1", "Kök 1 dal 1 yaprak 1", [
      { id: "root-1", title: "Kök 1" },
      { id: "branch-1-1", title: "Kök 1 dal 1" },
    ]);
    harness.reset("#/learning?focus=leaf-1-1-1");

    renderPage();
    await waitFor(() => expect(screen.getByLabelText("Yeni konu başlığı")).toBeTruthy());
    fireEvent.change(screen.getByLabelText("Yeni konu başlığı"), { target: { value: "Yeni yaprak" } });
    fireEvent.click(screen.getByLabelText("Konu ekle"));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/study/topics", {
        title: "Yeni yaprak",
        area_id: "a1",
        parent_id: "leaf-1-1-1",
      }),
    );
    await waitFor(() => expect(harness.state.hash).toContain("focus=yeni-1"));
    expect(vi.mocked(invalidateAfter)).toHaveBeenCalledWith("study.write");
  });

  it("alan yönetimi: yeniden adlandırma/arşivleme PATCH, kalıcı silme DELETE + onay ister", async () => {
    const post = vi.mocked(api.post);
    const patch = vi.mocked(api.patch);
    const del = vi.mocked(api.del);
    patch.mockResolvedValue(AREAS[0]);
    del.mockResolvedValue(undefined);
    post.mockResolvedValue({ id: "a3", title: "Yeni alan" });
    renderPage();
    await waitFor(() => expect(screen.getByText("Alan yönetimi")).toBeTruthy());

    fireEvent.click(screen.getByText("Alan yönetimi"));
    const rename = await screen.findByLabelText("Git adı");
    fireEvent.change(rename, { target: { value: "Git 2" } });
    fireEvent.blur(rename);
    await waitFor(() => expect(patch).toHaveBeenCalledWith("/study/areas/a1", { title: "Git 2" }));

    fireEvent.click(screen.getByLabelText("Git alanını arşivle"));
    await waitFor(() => expect(patch).toHaveBeenCalledWith("/study/areas/a1", { archived: true }));

    // Kalici silme ayri ve acik onay ister (etkilenecek konu/kaynak sayisi ile).
    fireEvent.click(screen.getAllByTitle("Alanı kalıcı olarak sil")[0]);
    await waitFor(() => expect(confirmDialog).toHaveBeenCalled());
    await waitFor(() => expect(del).toHaveBeenCalledWith("/study/areas/a1"));
    expect(vi.mocked(invalidateAfter)).toHaveBeenCalledWith("study.write");
  });
});
