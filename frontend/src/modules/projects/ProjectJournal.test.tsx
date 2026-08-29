// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { todayKey } from "@/lib/date";
import { ProjectJournal } from "./ProjectJournal";

type MutationOptions = {
  mutationFn: (body: string) => Promise<unknown>;
  onSuccess?: () => void;
};

const harness = vi.hoisted(() => ({
  apiPut: vi.fn(),
  invalidate: vi.fn(),
}));

vi.mock("@/core/api", () => ({
  api: { get: vi.fn(), put: harness.apiPut },
  qs: () => "?limit=60",
}));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(() => {
    const today = todayKey();
    const previousDay = new Date(`${today}T00:00:00Z`);
    previousDay.setUTCDate(previousDay.getUTCDate() - 1);
    return {
      data: [
        {
          day: today,
          note: {
            id: "note-1",
            body: "Eski günlük notu",
            title: "Eski günlük notu",
            project_id: "project-1",
            journal_day: today,
            pinned: false,
            created_at: "2026-08-29T08:00:00Z",
            updated_at: "2026-08-29T08:00:00Z",
          },
          events: [
            {
              id: 3,
              verb: "note.created",
              entity_id: "note-1",
              entity_type: "note",
              title: null,
              payload: {},
              occurred_at: "2026-08-29T10:00:00Z",
            },
            {
              id: 2,
              verb: "custom.internal_event",
              entity_id: "project-1",
              entity_type: "project",
              title: "Bilinmeyen olay",
              payload: {},
              occurred_at: "2026-08-29T09:30:00Z",
            },
            {
              id: 1,
              verb: "todo.completed",
              entity_id: "todo-1",
              entity_type: "todo",
              title: "Entegrasyonu tamamla",
              payload: {},
              occurred_at: "2026-08-29T09:00:00Z",
            },
          ],
        },
        {
          day: previousDay.toISOString().slice(0, 10),
          note: {
            id: "note-previous",
            body: "Geçmiş gün notu",
            title: "Geçmiş gün notu",
            project_id: "project-1",
            journal_day: previousDay.toISOString().slice(0, 10),
            pinned: false,
            created_at: "2026-08-28T08:00:00Z",
            updated_at: "2026-08-28T08:00:00Z",
          },
          events: [],
        },
      ],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    };
  }),
  useMutation: vi.fn((options: MutationOptions) => ({
    mutate: vi.fn(async (body: string) => {
      await options.mutationFn(body);
      options.onSuccess?.();
    }),
    isPending: false,
  })),
}));

describe("ProjectJournal", () => {
  beforeEach(() => {
    harness.apiPut.mockReset();
    harness.apiPut.mockResolvedValue({});
    harness.invalidate.mockReset();
  });
  afterEach(cleanup);

  it("bugunu secer, gelecegi kapatir ve not ile olaylari ayni gun grubunda gosterir", () => {
    const { container } = render(<ProjectJournal projectId="project-1" />);

    const day = screen.getByLabelText("Gün") as HTMLInputElement;
    expect(day.value).toBe(todayKey());
    expect(day.max).toBe(todayKey());
    expect(screen.getByDisplayValue("Eski günlük notu")).toBeTruthy();
    expect(screen.queryByText("note.created")).toBeNull();
    expect(screen.queryByText("custom.internal_event")).toBeNull();
    expect(screen.getByText("Proje hareketi")).toBeTruthy();

    const active = screen.getByTestId("project-journal-active-day");
    expect(within(active).getByText("Entegrasyonu tamamla")).toBeTruthy();
    expect(container.querySelector(`[data-project-journal-day="${todayKey()}"]`)).toBeNull();
    expect(screen.getByText("Geçmiş gün notu")).toBeTruthy();
  });

  it("gecmis gunu secince notu ve hareketleri aktif calisma yuzeyine tasir", async () => {
    const { container } = render(<ProjectJournal projectId="project-1" />);
    const today = todayKey();
    const previousDay = new Date(`${today}T00:00:00Z`);
    previousDay.setUTCDate(previousDay.getUTCDate() - 1);
    const history = container.querySelector(`[data-project-journal-day="${previousDay.toISOString().slice(0, 10)}"]`);

    expect(history).not.toBeNull();
    fireEvent.click(within(history as HTMLElement).getByRole("button"));

    await waitFor(() =>
      expect(
        within(screen.getByTestId("project-journal-active-day")).getByDisplayValue("Geçmiş gün notu"),
      ).toBeTruthy(),
    );
  });

  it("alandan cikinca tek gunluk PUT'u atar ve ilgili sorgulari tazeler", async () => {
    render(<ProjectJournal projectId="project-1" />);
    const editor = screen.getByLabelText("Günlük notu");

    fireEvent.change(editor, { target: { value: "Yeni günlük notu" } });
    fireEvent.blur(editor);

    await waitFor(() =>
      expect(harness.apiPut).toHaveBeenCalledWith(`/projects/project-1/journal/${todayKey()}`, {
        body: "Yeni günlük notu",
      }),
    );
    expect(harness.invalidate).toHaveBeenCalledWith("note.write", "project.write", "link.write");
  });

  it("bos editoru notu kaldirma semantigiyle gonderir", async () => {
    render(<ProjectJournal projectId="project-1" />);
    const editor = screen.getByLabelText("Günlük notu");

    fireEvent.change(editor, { target: { value: "" } });
    fireEvent.blur(editor);

    await waitFor(() =>
      expect(harness.apiPut).toHaveBeenCalledWith(`/projects/project-1/journal/${todayKey()}`, { body: "" }),
    );
  });
});
