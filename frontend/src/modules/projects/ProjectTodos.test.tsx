import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Project } from "@/core/types";
import { createProjectTodo, ProjectTodos } from "./ProjectTodos";

type MutationOptions = {
  mutationFn?: () => Promise<unknown> | unknown;
  onSuccess?: () => void;
};

const harness = vi.hoisted(() => ({
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  mutations: [] as MutationOptions[],
}));

vi.mock("@/core/api", () => ({ api: { post: harness.apiPost } }));
vi.mock("@/lib/hooks", () => ({
  useInvalidate: () => harness.invalidate,
  useOnline: () => true,
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
    harness.mutations.length = 0;
  });

  it("creates and links a project todo through the component mutation in one request", async () => {
    harness.apiPost.mockResolvedValue({ id: "todo-1" });
    renderToStaticMarkup(<ProjectTodos project={project} />);

    const add = harness.mutations[0];
    await add.mutationFn?.();

    expect(harness.apiPost).toHaveBeenCalledTimes(1);
    expect(harness.apiPost).toHaveBeenCalledWith("/todos", {
      title: "",
      project_id: "project-1",
    });
    expect(harness.apiPost.mock.calls[0][1]).not.toHaveProperty("milestone_id");

    add.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith(
      "projects", "project-todos", "project-timeline", "todos", "activity",
    );
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
