// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  useQuery: vi.fn(() => ({
    data: [
      {
        day: todayKey(),
        note: {
          id: "note-1",
          body: "Eski günlük notu",
          title: "Eski günlük notu",
          project_id: "project-1",
          journal_day: todayKey(),
          pinned: false,
          created_at: "2026-08-29T08:00:00Z",
          updated_at: "2026-08-29T08:00:00Z",
        },
        events: [
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
    ],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })),
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
    render(<ProjectJournal projectId="project-1" />);

    const day = screen.getByLabelText("Gün") as HTMLInputElement;
    expect(day.value).toBe(todayKey());
    expect(day.max).toBe(todayKey());
    expect(screen.getByDisplayValue("Eski günlük notu")).toBeTruthy();
    expect(screen.getByText("Entegrasyonu tamamla")).toBeTruthy();
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
