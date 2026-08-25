import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Project } from "@/core/types";
import { createProjectTodo, ProjectTodos } from "./ProjectTodos";

type MutationOptions = {
  mutationFn?: () => Promise<unknown> | unknown;
  onSuccess?: () => void;
};
type InputProps = { ariaLabel?: string; onChange: (value: string) => void };
type SelectProps = { ariaLabel?: string; onChange: (value: string) => void };

const harness = vi.hoisted(() => ({
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  inputs: [] as InputProps[],
  mutations: [] as MutationOptions[],
  selects: [] as SelectProps[],
  stateCursor: 0,
  stateValues: [] as unknown[],
}));

vi.mock("react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react")>();
  return {
    ...actual,
    useState: (initial: unknown | (() => unknown)) => {
      const index = harness.stateCursor++;
      if (!(index in harness.stateValues)) {
        harness.stateValues[index] = typeof initial === "function" ? initial() : initial;
      }
      return [harness.stateValues[index], (value: unknown) => { harness.stateValues[index] = value; }];
    },
  };
});
vi.mock("@/core/api", () => ({ api: { post: harness.apiPost } }));
vi.mock("@/core/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/ui")>();
  return {
    ...actual,
    Input: (props: InputProps) => { harness.inputs.push(props); return null; },
    Select: (props: SelectProps) => { harness.selects.push(props); return null; },
  };
});
vi.mock("@/lib/hooks", () => ({
  useOnline: () => true,
}));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn((options: MutationOptions) => {
    harness.mutations.push(options);
    return { mutate: vi.fn(), isPending: false };
  }),
  useQuery: vi.fn(() => ({ data: [] })),
}));

const project = { id: "project-1", title: "Proje", milestones: [] } as unknown as Project;

describe("project todo integration", () => {
  beforeEach(() => {
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.inputs.length = 0;
    harness.mutations.length = 0;
    harness.selects.length = 0;
    harness.stateCursor = 0;
    harness.stateValues = [];
  });

  it("wires selected milestone and title form state into the one-request component mutation", async () => {
    harness.apiPost.mockResolvedValue({ id: "todo-1" });
    const projectWithMilestone = {
      ...project,
      milestones: [{
        id: "milestone-1", project_id: "project-1", title: "İlk adım", due_at: null, completed_at: null, position: 0,
      }],
    };
    renderToStaticMarkup(<ProjectTodos project={projectWithMilestone} />);

    harness.inputs.find((input) => input.ariaLabel === "Yeni görev")?.onChange("  Görevi bitir  ");
    harness.selects.find((select) => select.ariaLabel === "Kilometre taşı")?.onChange("milestone-1");

    harness.inputs.length = 0;
    harness.mutations.length = 0;
    harness.selects.length = 0;
    harness.stateCursor = 0;
    renderToStaticMarkup(<ProjectTodos project={projectWithMilestone} />);

    const add = harness.mutations[0];
    await add.mutationFn?.();

    expect(harness.apiPost).toHaveBeenCalledTimes(1);
    expect(harness.apiPost).toHaveBeenCalledWith("/todos", {
      title: "Görevi bitir",
      project_id: "project-1",
      milestone_id: "milestone-1",
    });

    add.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("project.write");
  });

  it("trims titles and omits a blank milestone in the atomic helper", async () => {
    harness.apiPost.mockResolvedValue({ id: "todo-1" });

    await createProjectTodo("project-1", "  Görevi bitir  ", "");

    expect(harness.apiPost).toHaveBeenCalledTimes(1);
    expect(harness.apiPost).toHaveBeenCalledWith("/todos", {
      title: "Görevi bitir",
      project_id: "project-1",
    });
    expect(harness.apiPost.mock.calls[0][1]).not.toHaveProperty("milestone_id");
  });
});
