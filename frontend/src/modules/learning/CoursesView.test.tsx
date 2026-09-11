// @vitest-environment jsdom
/**
 * Kurslar gorunumu (Faz 8): liste/filtre uclari, tek-istekli ilerleme
 * commit'i, olusturma/arsivleme/silme akislari, tarih gosterimi ve sertifika
 * baglama. Gercek react-query + gercek bilesen; yalnizca ag ve yonlendirme
 * taklit edilir.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { components } from "@/generated/api-schema";
import { CoursesView } from "./CoursesView";

type Course = components["schemas"]["CourseOut"];

const harness = vi.hoisted(() => ({
  apiDel: vi.fn(),
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  navigate: vi.fn(),
  routeParams: "",
}));

vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return {
    ...actual,
    api: { ...actual.api, del: harness.apiDel, get: harness.apiGet, patch: harness.apiPatch, post: harness.apiPost },
  };
});
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/core/dialog", () => ({ confirmDialog: vi.fn(async () => true) }));
vi.mock("@/app/router", () => ({
  useHashRoute: () => ({ path: "/learning", params: new URLSearchParams(harness.routeParams) }),
  navigate: (path: string) => harness.navigate(path),
}));

const course = (over: Partial<Course>): Course => ({
  id: "c1",
  title: "Lineer Cebir",
  platform: "Udemy",
  url: null,
  status: "in_progress",
  progress_pct: 40,
  started_at: "2026-08-01T00:00:00Z",
  completed_at: null,
  notes: null,
  archived: false,
  area_ids: [],
  topic_ids: [],
  resource_count: 0,
  certificate_entity_id: null,
  ...over,
});

const COURSES: Course[] = [
  course({}),
  course({
    id: "c2",
    title: "Biten kurs",
    status: "done",
    progress_pct: 100,
    completed_at: "2026-09-01T00:00:00Z",
    archived: true,
  }),
];

function renderView() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <CoursesView />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
    configurable: true,
    value: vi.fn(),
  });
  harness.apiDel.mockReset().mockResolvedValue(undefined);
  harness.apiPost.mockReset().mockResolvedValue(course({}));
  harness.apiPatch.mockReset().mockResolvedValue(course({}));
  harness.invalidate.mockReset();
  harness.navigate.mockReset();
  harness.routeParams = "";
  harness.apiGet.mockReset().mockImplementation(async (path: string) => {
    if (path.startsWith("/courses")) return COURSES;
    if (path.startsWith("/study/areas")) {
      return [{ id: "a1", title: "Matematik", color: null, active: true, position: 0 }];
    }
    if (path.startsWith("/study/topics/")) {
      return { topic: { id: "t1", title: "Türev" }, ancestors: [], resources: [], stats: {}, progress: {} };
    }
    return [];
  });
});
afterEach(cleanup);

describe("CoursesView", () => {
  it("kurslari listeler ve arsiv filtresini sorguya cevirir", async () => {
    renderView();

    expect(await screen.findByText("Lineer Cebir")).toBeTruthy();
    expect(screen.getByText("Biten kurs")).toBeTruthy();
    expect(harness.apiGet).toHaveBeenCalledWith("/courses");

    fireEvent.click(screen.getByLabelText("Arşivlenenleri göster"));
    await waitFor(() => expect(harness.apiGet).toHaveBeenCalledWith("/courses?include_archived=true"));
  });

  it("bagli alan adini ve tarihleri gorunur yazar", async () => {
    harness.apiGet.mockImplementation(async (path: string) => {
      if (path.startsWith("/courses")) return [course({ area_ids: ["a1"], started_at: "2026-08-01T00:00:00Z" })];
      if (path.startsWith("/study/areas")) {
        return [{ id: "a1", title: "Matematik", color: null, active: true, position: 0 }];
      }
      return [];
    });
    renderView();

    const row = (await screen.findByText("Lineer Cebir")).closest("[id]");
    // Bagli alan adi cozulur, tarihler tr-TR bicimiyle yazilir; bitis yoksa "—".
    expect(row?.textContent).toContain("Matematik");
    expect(row?.textContent).toContain("Başlangıç: 01.08.2026");
    expect(row?.textContent).toContain("Bitiş: —");
  });

  it("kaydiriciyi hizli oynatmak TEK PATCH uretir (400 ms debounce, son deger)", async () => {
    renderView();
    const slider = await screen.findByRole("slider", { name: "İlerleme: Lineer Cebir" });

    fireEvent.change(slider, { target: { value: "55" } });
    fireEvent.change(slider, { target: { value: "70" } });
    fireEvent.change(slider, { target: { value: "85" } });
    expect(harness.apiPatch).not.toHaveBeenCalled();

    await waitFor(() => expect(harness.apiPatch).toHaveBeenCalledTimes(1));
    expect(harness.apiPatch).toHaveBeenCalledWith("/courses/c1", { progress_pct: 85 });
    await waitFor(() => expect(harness.invalidate).toHaveBeenCalledWith("learning.write"));
  });

  it("yeni kurs olusturur ve learning.write tazeler", async () => {
    renderView();
    fireEvent.click(await screen.findByRole("button", { name: /Kurs ekle/ }));

    fireEvent.change(screen.getByPlaceholderText("Kurs adı"), { target: { value: "Yeni kurs" } });
    fireEvent.click(screen.getByRole("button", { name: "Ekle" }));

    await waitFor(() =>
      expect(harness.apiPost).toHaveBeenCalledWith("/courses", {
        title: "Yeni kurs",
        platform: null,
        url: null,
        status: "planned",
        notes: null,
        area_ids: [],
      }),
    );
    await waitFor(() => expect(harness.invalidate).toHaveBeenCalledWith("learning.write"));
  });

  it("kursu arsivler ve onay sonrasi siler", async () => {
    renderView();
    fireEvent.click(await screen.findByRole("button", { name: /Arşivle/ }));
    await waitFor(() => expect(harness.apiPatch).toHaveBeenCalledWith("/courses/c1", { archived: true }));

    fireEvent.click(screen.getAllByRole("button", { name: /Sil/ })[0]);
    await waitFor(() => expect(harness.apiDel).toHaveBeenCalledWith("/courses/c1"));
  });

  it("sertifika baglarken arama sonucunu kursa yazar", async () => {
    harness.apiGet.mockImplementation(async (path: string) => {
      if (path.startsWith("/courses")) return [course({})];
      if (path.startsWith("/study/areas")) return [];
      if (path.startsWith("/search")) return { Belge: [{ id: "d1", type: "document", title: "Sertifika PDF" }] };
      return [];
    });
    renderView();

    fireEvent.click(await screen.findByRole("button", { name: "Sertifika bağla" }));
    const box = screen.getByPlaceholderText("Belge ya da not ara (en az 2 harf)");
    fireEvent.change(box, { target: { value: "sertifika" } });

    const hit = await screen.findByRole("button", { name: /Sertifika PDF/ });
    fireEvent.click(hit);

    await waitFor(() => expect(harness.apiPatch).toHaveBeenCalledWith("/courses/c1", { certificate_entity_id: "d1" }));
    expect(harness.apiGet).toHaveBeenCalledWith("/search?q=sertifika&limit=8&grouped=true");
  });

  it("?course= derin baglantisindaki satiri isaretler", async () => {
    harness.routeParams = "view=courses&course=c2";
    renderView();

    const row = (await screen.findByText("Biten kurs")).closest("[id]");
    expect(row?.getAttribute("id")).toBe("course-c2");
    expect(row?.getAttribute("aria-current")).toBe("true");
  });
});
