// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "@/core/ui";
import { WeeklyPlannerPage } from "./WeeklyPlannerPage";

type MutationOptions = {
  mutationFn?: (variables: { active: string; target: string }) => Promise<unknown> | unknown;
  onSuccess?: (data: unknown, variables: { active: string; target: string }) => void;
};
type QueryOptions = { queryKey: readonly unknown[] };

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
}));

vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: { children: unknown }) => children,
  DragOverlay: ({ children }: { children: unknown }) => children,
  PointerSensor: class {},
  KeyboardSensor: class {},
  useSensor: vi.fn(),
  useSensors: vi.fn(),
  pointerWithin: vi.fn(),
  rectIntersection: vi.fn(),
  useDraggable: () => ({
    setNodeRef: vi.fn(),
    listeners: {},
    attributes: {},
    transform: null,
    isDragging: false,
  }),
  useDroppable: () => ({ setNodeRef: vi.fn(), isOver: false }),
}));
vi.mock("@/core/api", () => ({
  api: { get: harness.apiGet, patch: harness.apiPatch, post: harness.apiPost },
  qs: () => "",
}));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery: vi.fn((options: QueryOptions) => ({
      data:
        options.queryKey[0] === "todos"
          ? [
              {
                id: "todo-1",
                title: "Klavye ile planlanacak",
                status: "open",
                priority: 2,
                tags: [],
              },
            ]
          : [],
    })),
    useMutation: vi.fn((options: MutationOptions) => ({
      mutate: async (variables: { active: string; target: string }) => {
        await options.mutationFn?.(variables);
        options.onSuccess?.(undefined, variables);
      },
      isPending: false,
    })),
  };
});

describe("WeeklyPlannerPage", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.apiPatch.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.apiPost.mockResolvedValue({});
  });
  afterEach(cleanup);

  it("lets keyboard users select a backlog task and place it on a day", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ToastProvider>
          <WeeklyPlannerPage />
        </ToastProvider>
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Klavye ile planlanacak görevini planlamak için seç" }));
    const place = screen.getAllByRole("button", { name: /Seçili görevi .* gününe planla/ })[0];
    const day = place.getAttribute("title")?.match(/(\d{4}-\d{2}-\d{2})/)?.[1];
    expect(day).toBeTruthy();
    fireEvent.click(place);

    await waitFor(() =>
      expect(harness.apiPost).toHaveBeenCalledWith("/plan", {
        entity_id: "todo-1",
        day,
      }),
    );
    expect(harness.invalidate).toHaveBeenCalledWith("plan.write");
  });

  it("planlanan gorev 'Planlanmamış' listesinden ANINDA duser", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ToastProvider>
          <WeeklyPlannerPage />
        </ToastProvider>
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Klavye ile planlanacak görevini planlamak için seç" }));
    fireEvent.click(screen.getAllByRole("button", { name: /Seçili görevi .* gününe planla/ })[0]);

    // `plan` sorgusu bu testte hic yeni slot dondurmuyor: gorev yalnizca
    // secim defteri sayesinde dusuyorsa davranis aninda demektir.
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Klavye ile planlanacak görevini planlamak için seç" })).toBeNull(),
    );
    expect(screen.getByText("Açık görevlerin hepsi planlandı.")).toBeTruthy();
  });

  it("haftalık görünümde aynı görev oluşturucusu yeni işi seçili haftaya planlar", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ToastProvider>
          <WeeklyPlannerPage />
        </ToastProvider>
      </QueryClientProvider>,
    );
    fireEvent.change(screen.getByLabelText("Görev başlığı"), { target: { value: "Yeni haftalık iş" } });
    fireEvent.click(screen.getByRole("button", { name: "Ekle" }));

    await waitFor(() =>
      expect(harness.apiPost).toHaveBeenCalledWith(
        "/todos",
        expect.objectContaining({
          title: "Yeni haftalık iş",
          plan_day: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
        }),
      ),
    );
  });
});
