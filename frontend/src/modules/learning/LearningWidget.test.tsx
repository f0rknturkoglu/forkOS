// @vitest-environment jsdom
/**
 * Ogrenme widget'i (Faz 12): kurs ve konu satirlari ayrisir ve her tip kendi
 * derin baglantisina gider; bos durumda "Ogrenmeye git" cikar.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LearningWidget } from "./LearningWidget";

const harness = vi.hoisted(() => ({ apiGet: vi.fn() }));

vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return { ...actual, api: { ...actual.api, get: harness.apiGet } };
});

const staleIso = new Date(Date.now() - 25 * 86_400_000).toISOString();

function renderWidget() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <LearningWidget />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  harness.apiGet.mockReset().mockImplementation(async (path: string) => {
    if (path === "/courses") {
      return [
        {
          id: "c1",
          title: "Lineer Cebir",
          status: "in_progress",
          progress_pct: 40,
          platform: null,
          url: null,
          started_at: null,
          completed_at: null,
          notes: null,
          archived: false,
          area_ids: [],
          topic_ids: [],
          resource_count: 0,
          certificate_entity_id: null,
        },
        {
          id: "c2",
          title: "Biten kurs",
          status: "done",
          progress_pct: 100,
          platform: null,
          url: null,
          started_at: null,
          completed_at: null,
          notes: null,
          archived: false,
          area_ids: [],
          topic_ids: [],
          resource_count: 0,
          certificate_entity_id: null,
        },
      ];
    }
    if (path.startsWith("/study/stale")) {
      return {
        items: [
          {
            id: "t1",
            title: "Türev",
            area_id: "a1",
            status: "in_progress",
            parent_id: null,
            position: 0,
            last_studied_at: staleIso,
            next_review_at: null,
            mastery: null,
            confidence: null,
            interval_days: 0,
            review_count: 0,
            last_reviewed_at: null,
          },
        ],
        limit: 3,
        offset: 0,
        total: 1,
      };
    }
    return [];
  });
});
afterEach(cleanup);

describe("LearningWidget", () => {
  it("kurs ve konu satirlarini ayirir, deep-link'leri dogru kurar", async () => {
    renderWidget();

    const course = (await screen.findByText("Lineer Cebir")).closest("a");
    expect(course?.getAttribute("href")).toBe("#/learning?view=courses&course=c1");
    expect(course?.parentElement?.textContent).toContain("Kurs");

    const topic = (await screen.findByText("Türev")).closest("a");
    expect(topic?.getAttribute("href")).toBe("#/learning?focus=t1");
    expect(topic?.parentElement?.textContent).toContain("Konu");

    // Biten kurs listede yok; stale sorgusu 21 gun ile ve sinirli cekilir.
    expect(screen.queryByText("Biten kurs")).toBeNull();
    expect(harness.apiGet).toHaveBeenCalledWith("/study/stale?days=21&limit=3");
  });

  it("konu satirinda son calisma gununu yazar", async () => {
    renderWidget();
    const topic = (await screen.findByText("Türev")).closest("a");
    expect(topic?.parentElement?.textContent).toContain(
      `Son çalışma: ${Math.floor((Date.now() - new Date(staleIso).getTime()) / 86_400_000)} gün önce`,
    );
  });

  it("tekrar tarihi varsa onu gosterir", async () => {
    harness.apiGet.mockImplementation(async (path: string) => {
      if (path === "/courses") return [];
      return {
        items: [
          {
            id: "t2",
            title: "İntegral",
            area_id: "a1",
            status: "in_progress",
            parent_id: null,
            position: 0,
            last_studied_at: staleIso,
            next_review_at: "2026-09-20T00:00:00Z",
            mastery: null,
            confidence: null,
            interval_days: 0,
            review_count: 0,
            last_reviewed_at: null,
          },
        ],
        limit: 3,
        offset: 0,
        total: 1,
      };
    });
    renderWidget();

    const topic = (await screen.findByText("İntegral")).closest("a");
    expect(topic?.parentElement?.textContent).toContain("Tekrar: 20.09.2026");
  });

  it("bos durumda ogrenmeye yonlendirir", async () => {
    harness.apiGet.mockImplementation(async (path: string) =>
      path === "/courses" ? [] : { items: [], limit: 3, offset: 0, total: 0 },
    );
    renderWidget();

    expect(await screen.findByText("Devam eden kurs ya da tekrar bekleyen konu yok.")).toBeTruthy();
    expect(screen.getByText("Öğrenmeye git").closest("a")?.getAttribute("href")).toBe("#/learning");
  });
});
