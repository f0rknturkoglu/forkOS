import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/core/api";
import { createProjectTodo } from "./ProjectTodos";

vi.mock("@/core/api", () => ({ api: { post: vi.fn() } }));

describe("project todo integration", () => {
  beforeEach(() => vi.clearAllMocks());

  it("creates and links a project todo in one request", async () => {
    vi.mocked(api.post).mockResolvedValue({ id: "todo-1" });

    await createProjectTodo("project-1", "Görevi bitir", "milestone-1");

    expect(api.post).toHaveBeenCalledTimes(1);
    expect(api.post).toHaveBeenCalledWith("/todos", {
      title: "Görevi bitir",
      project_id: "project-1",
      milestone_id: "milestone-1",
    });
  });
});
