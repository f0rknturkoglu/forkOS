// @vitest-environment jsdom
/**
 * ProjectActivityTimeline — gunluge gore proje hareketleri (salt okunur).
 *
 * Gunluk NOTU artik bu yuzeyde degildir: yalnizca olaylar gruplanir ve
 * Vault'a tasinan eski `note.*` olaylari proje hareketi sayilmaz.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/core/api";
import { todayKey } from "@/lib/date";
import { ProjectActivityTimeline } from "./ProjectActivityTimeline";

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return { ...actual, api: { get: harness.apiGet } };
});

function previousDayKey(): string {
  const previousDay = new Date(`${todayKey()}T00:00:00Z`);
  previousDay.setUTCDate(previousDay.getUTCDate() - 1);
  return previousDay.toISOString().slice(0, 10);
}

const groups = [
  {
    day: todayKey(),
    events: [
      {
        id: 3,
        verb: "note.created",
        entity_id: "note-1",
        entity_type: "note",
        title: null,
        payload: {},
        occurred_at: "2026-09-20T10:00:00Z",
      },
      {
        id: 2,
        verb: "custom.internal_event",
        entity_id: "project-1",
        entity_type: "project",
        title: "Bilinmeyen olay",
        payload: {},
        occurred_at: "2026-09-20T09:30:00Z",
      },
      {
        id: 1,
        verb: "todo.completed",
        entity_id: "todo-1",
        entity_type: "todo",
        title: "Entegrasyonu tamamla",
        payload: {},
        occurred_at: "2026-09-20T09:00:00Z",
      },
    ],
  },
  {
    day: previousDayKey(),
    events: [
      {
        id: 4,
        verb: "project.created",
        entity_id: "project-1",
        entity_type: "project",
        title: "Geçmiş hareket",
        payload: {},
        occurred_at: "2026-09-19T08:00:00Z",
      },
    ],
  },
];

function renderTimeline() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ProjectActivityTimeline projectId="project-1" />
    </QueryClientProvider>,
  );
}

describe("ProjectActivityTimeline", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.apiGet.mockResolvedValue(groups);
  });

  afterEach(cleanup);

  it("gunluk ucundan okur, bugunu secer ve gelecek gunu kapatir", async () => {
    renderTimeline();

    await screen.findByText("Entegrasyonu tamamla");
    expect(harness.apiGet).toHaveBeenCalledWith("/projects/project-1/journal?limit=60");

    const day = screen.getByLabelText("Gün") as HTMLInputElement;
    expect(day.value).toBe(todayKey());
    expect(day.max).toBe(todayKey());

    // Not olaylari ve bilinmeyen olaylar proje hareketi degildir.
    expect(screen.queryByText("note.created")).toBeNull();
    expect(screen.queryByText("custom.internal_event")).toBeNull();
    expect(screen.getByText("Proje hareketi")).toBeTruthy();

    const active = screen.getByTestId("project-journal-active-day");
    expect(within(active).getByText("Entegrasyonu tamamla")).toBeTruthy();
    // Bugun aktif yuzeyde; gecmis grubunda tekrar listelenmez.
    expect(document.querySelector(`[data-project-journal-day="${todayKey()}"]`)).toBeNull();
  });

  it("gecmis gun secilince o gunun hareketleri aktif calisma yuzeyine tasinir", async () => {
    renderTimeline();
    await screen.findByText("Entegrasyonu tamamla");
    const history = document.querySelector(`[data-project-journal-day="${previousDayKey()}"]`);

    expect(history).not.toBeNull();
    fireEvent.click(within(history as HTMLElement).getByRole("button"));

    await waitFor(() =>
      expect(within(screen.getByTestId("project-journal-active-day")).getByText("Geçmiş hareket")).toBeTruthy(),
    );
    expect(within(screen.getByTestId("project-journal-active-day")).queryByText("Entegrasyonu tamamla")).toBeNull();
  });

  it("uc hata verirse hata durumunu gosterir", async () => {
    harness.apiGet.mockRejectedValue(new ApiError(500, "patladı", null));
    renderTimeline();

    expect(await screen.findByText("Proje günlüğü alınamadı.")).toBeTruthy();
  });
});
