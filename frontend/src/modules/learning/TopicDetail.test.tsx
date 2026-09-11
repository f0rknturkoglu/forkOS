// @vitest-environment jsdom
/**
 * TopicDetail — konu calisma alani.
 *
 * Kabul kriterleri burada: "siradaki aksiyon" secimi (6 baglam), gorev
 * olusturma idempotency mesaji, durum degisimi, 404 bos durumu, silme
 * etki diyalogu.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DialogHost } from "@/core/dialog";
import { ToastProvider } from "@/core/ui";
import { TopicDetail, pickNextAction, type NextActionInput, type TopicTab } from "./TopicDetail";

const harness = vi.hoisted(() => ({
  apiDel: vi.fn(),
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  navigate: vi.fn(),
}));

vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return {
    ...actual,
    api: { del: harness.apiDel, get: harness.apiGet, patch: harness.apiPatch, post: harness.apiPost },
  };
});
vi.mock("@/core/invalidation", () => ({ invalidateAfter: (...events: string[]) => harness.invalidate(...events) }));
vi.mock("@/app/router", () => ({
  navigate: harness.navigate,
  useHashRoute: () => ({ path: "/learning", params: new URLSearchParams() }),
}));
vi.mock("@/lib/hooks", () => ({
  useOnline: () => true,
  useDebounced: <T,>(value: T) => value,
}));

const detail = {
  topic: {
    id: "t1",
    title: "Versiyon Kontrol Temelleri",
    area_id: "a1",
    parent_id: null,
    status: "in_progress",
    confidence: 3,
    target_min: 60,
    position: 0,
    mastery: 40,
    last_studied_at: null,
    interval_days: 2,
    ease: 2.5,
    review_count: 1,
    last_reviewed_at: null,
    next_review_at: null,
  },
  ancestors: [{ id: "root", title: "Git" }],
  resources: [
    {
      id: "r1",
      topic_id: "t1",
      title: "Pro Git",
      url: "https://git-scm.com/book",
      kind: "book",
      position: 0,
      completed_at: null,
      note: null,
      estimated_min: 30,
      last_opened_at: null,
      source: "manual",
      bookmark_id: null,
      course_id: null,
    },
  ],
  progress: { total: 3, done: 1, pct: 33 },
  stats: { minutes: 45, sessions: 2, week_minutes: 20, last_studied_at: "2026-09-10T10:00:00Z" },
  open_todo: null,
  note_count: 2,
  flashcard_deck_count: 1,
  review: {
    due: false,
    ease: 2.5,
    interval_days: 2,
    last_reviewed_at: null,
    mastery: 40,
    next_review_at: null,
    review_count: 1,
  },
};

function renderDetail(props: { tab?: TopicTab; onTabChange?: (tab: TopicTab) => void; onDeleted?: () => void } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onTabChange = props.onTabChange ?? vi.fn();
  const onDeleted = props.onDeleted ?? vi.fn();
  const utils = render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <DialogHost />
        <TopicDetail topicId="t1" tab={props.tab ?? "genel"} onTabChange={onTabChange} onDeleted={onDeleted} />
      </ToastProvider>
    </QueryClientProvider>,
  );
  return { ...utils, onTabChange, onDeleted };
}

const action = (over: Partial<NextActionInput> = {}) => ({
  openTodo: null,
  pomodoroActive: false,
  reviewDue: false,
  status: "in_progress",
  resourceDone: 0,
  resourceTotal: 0,
  ...over,
});

describe("pickNextAction", () => {
  it("acik gorev varsa gorevi acar (en yuksek oncelik)", () => {
    expect(
      pickNextAction(action({ openTodo: { id: "todo-1" }, reviewDue: true, resourceDone: 1, resourceTotal: 2 })),
    ).toEqual({ id: "todo", label: "Görevi aç" });
  });

  it("aktif pomodoro varsa odaga doner", () => {
    expect(
      pickNextAction(action({ pomodoroActive: true, reviewDue: true, resourceDone: 1, resourceTotal: 2 })),
    ).toEqual({
      id: "pomodoro",
      label: "Odağa dön",
    });
  });

  it("tekrar zamani geldiyse tekrar yapar", () => {
    expect(pickNextAction(action({ reviewDue: true, resourceDone: 1, resourceTotal: 2 }))).toEqual({
      id: "review",
      label: "Tekrar yap",
    });
  });

  it("hic kaynak tamamlanmadiysa calismaya baslatir", () => {
    expect(pickNextAction(action({ resourceDone: 0, resourceTotal: 4 }))).toEqual({
      id: "start",
      label: "Çalışmaya başla",
    });
  });

  it("eksik kaynak varsa siradaki kaynagi acar", () => {
    expect(pickNextAction(action({ resourceDone: 2, resourceTotal: 4 }))).toEqual({
      id: "next-resource",
      label: "Sıradaki kaynağı aç",
    });
  });

  it("tamamlanmis konuda bilgiyi tazelemeyi onerir", () => {
    expect(pickNextAction(action({ status: "done", resourceDone: 3, resourceTotal: 3 }))).toEqual({
      id: "refresh",
      label: "Bilgiyi tazele",
    });
  });
});

describe("TopicDetail", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.apiPost.mockReset();
    harness.apiPatch.mockReset();
    harness.apiDel.mockReset();
    harness.invalidate.mockReset();
    harness.navigate.mockReset();
    harness.apiGet.mockImplementation(async (path: string) => {
      if (path === "/study/topics/t1") return detail;
      if (path === "/pomodoro/active") return null;
      return [];
    });
  });

  afterEach(cleanup);

  it("ilk ekranda dort olcuyu AYRI gosterir (kaynak/odak/ustalik/hedef)", async () => {
    renderDetail();
    expect(await screen.findByRole("heading", { name: "Versiyon Kontrol Temelleri" })).toBeTruthy();
    expect(screen.getByText("Kaynak ilerlemesi")).toBeTruthy();
    expect(screen.getByRole("progressbar", { name: "Kaynak ilerlemesi" }).getAttribute("aria-valuenow")).toBe("33");
    expect(screen.getByText("Odak süresi")).toBeTruthy();
    expect(screen.getByText("45 dk")).toBeTruthy();
    expect(screen.getByText("Ustalık")).toBeTruthy();
    expect(screen.getByText("%40")).toBeTruthy();
    expect(screen.getByText("Hedef süre")).toBeTruthy();
    expect(screen.getByText("60 dk")).toBeTruthy();
    // Breadcrumb tiklanabilir.
    fireEvent.click(screen.getByRole("button", { name: "Git" }));
    expect(harness.navigate).toHaveBeenCalledWith("/learning?focus=root");
  });

  it("gorev olusturma idempotent oldugunda 'mevcut gorev acildi' mesajini verir", async () => {
    harness.apiPost.mockResolvedValue({ created: false, todo: { id: "todo-9", title: "Çalış" } });
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: /Görev oluştur/ }));

    await waitFor(() =>
      expect(harness.apiPost).toHaveBeenCalledWith("/study/topics/t1/todos", { plan_day: undefined }),
    );
    expect(await screen.findByText("Bu konunun açık görevi açıldı.")).toBeTruthy();
    expect(harness.invalidate).toHaveBeenCalledWith("todo.write", "study.write");
  });

  it("gorev olusturma yeni gorevde farkli mesaj verir", async () => {
    harness.apiPost.mockResolvedValue({ created: true, todo: { id: "todo-10", title: "Çalış" } });
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: /Görev oluştur/ }));
    expect(await screen.findByText("Görev oluşturuldu.")).toBeTruthy();
  });

  it("durum degisimi PATCH + study.write ile gider; 'Öğrenildi' once ustalik sorar", async () => {
    renderDetail();
    const statuses = await screen.findByRole("group", { name: "Konu durumu" });

    // TOPIC_STATUSES sirasi paylasilan sozlesme: not_started, in_progress, done.
    fireEvent.click(within(statuses).getAllByRole("button")[1]);
    await waitFor(() => expect(harness.apiPatch).toHaveBeenCalledWith("/study/topics/t1", { status: "in_progress" }));

    fireEvent.click(within(statuses).getAllByRole("button")[2]);
    // Durum hemen yazilmaz: once ustalik onay paneli cikar.
    expect(harness.apiPatch).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Öğrenildi olarak işaretle" }));
    await waitFor(() =>
      expect(harness.apiPatch).toHaveBeenCalledWith("/study/topics/t1", { status: "done", mastery: 40 }),
    );
    expect(harness.invalidate).toHaveBeenCalledWith("study.write");
  });

  it("404'te 'Konu bulunamadı' bos durumunu gosterir", async () => {
    harness.apiGet.mockImplementation(async (path: string) => {
      if (path === "/study/topics/t1") {
        const { ApiError } = await import("@/core/api");
        throw new ApiError(404, "bulunamadi", null);
      }
      return [];
    });
    renderDetail();
    expect(await screen.findByText("Konu bulunamadı")).toBeTruthy();
  });

  it("sekme degisimini disari bildirir (URL sozlesmesi)", async () => {
    const { onTabChange } = renderDetail();
    fireEvent.click(await screen.findByRole("tab", { name: "Tekrar" }));
    expect(onTabChange).toHaveBeenCalledWith("tekrar");
  });
});
