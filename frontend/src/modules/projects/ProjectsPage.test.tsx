// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Milestone, Project } from "@/core/types";
import { ProjectsPage } from "./ProjectsPage";

type QueryOptions = { queryKey: readonly unknown[] };
type MutationOptions = {
  mutationFn?: (variables: unknown) => Promise<unknown> | unknown;
  onSuccess?: (data: unknown, variables: unknown) => void;
};

const harness = vi.hoisted(() => ({
  focus: "",
  apiDel: vi.fn(),
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  queryData: {} as Record<string, unknown>,
}));

vi.mock("@/app/router", () => ({
  useHashRoute: () => ({ path: "/projects", params: new URLSearchParams(harness.focus) }),
}));
vi.mock("@/core/api", () => ({
  api: { del: harness.apiDel, get: harness.apiGet, patch: harness.apiPatch, post: harness.apiPost },
  qs: () => "",
}));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/core/dialog", () => ({
  confirmDialog: vi.fn(() => Promise.resolve(true)),
}));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery: vi.fn((options: QueryOptions) => {
      const key = String(options.queryKey[0]);
      return { data: harness.queryData[key], isLoading: false, isError: false };
    }),
    useMutation: vi.fn((options: MutationOptions) => ({
      mutate: async (variables: unknown) => {
        const result = await options.mutationFn?.(variables);
        options.onSuccess?.(result, variables);
      },
      isPending: false,
    })),
  };
});
// Agir alt paneller bu sayfanin secim mantigini test etmez; kendi testlerinde
// yasanir. Milestones + MilestoneTimeline gercek kalir (gorunurluk testi).
vi.mock("./GithubPanel", () => ({ GithubPanel: () => null }));
vi.mock("./ProjectTodos", () => ({ ProjectTodos: () => null }));
vi.mock("./ProjectJournal", () => ({ ProjectJournal: () => null }));
vi.mock("@/core/RelatedPanel", () => ({ RelatedPanel: () => null }));

const DAY = 86_400_000;
const at = (daysFromNow: number) => new Date(Date.now() + daysFromNow * DAY).toISOString();

function milestone(
  id: string,
  projectId: string,
  title: string,
  overrides: Partial<Milestone> = {},
): Milestone {
  return { id, project_id: projectId, title, due_at: null, completed_at: null, position: 0, ...overrides };
}

function project(id: string, title: string, milestones: Milestone[]): Project {
  return {
    id,
    title,
    status: "active",
    github_repo: null,
    url: null,
    stack: [],
    next_action: null,
    last_activity_at: null,
    position: 0,
    milestones,
  };
}

const alfa = project("p1", "Alfa", [milestone("m1", "p1", "Alfa adım")]);
const beta = project("p2", "Beta", [
  milestone("m1", "p2", "Beta 1. adım", { due_at: at(-12) }),
  milestone("m2", "p2", "Beta 2. adım", { due_at: at(3) }),
  milestone("m3", "p2", "Beta 3. adım", { due_at: at(-5), completed_at: at(-1) }),
  milestone("m4", "p2", "Beta 4. adım"),
]);
const gamma = project("p3", "Gamma", []);

const timelineSection = () => {
  const heading = screen.getByRole("heading", { name: "Zaman çizelgesi" });
  return heading.closest("section") as HTMLElement;
};

describe("ProjectsPage", () => {
  beforeEach(() => {
    harness.focus = "";
    harness.queryData = {};
    harness.apiDel.mockReset();
    harness.apiGet.mockReset();
    harness.apiPatch.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.apiDel.mockResolvedValue({});
    harness.apiGet.mockResolvedValue([]);
    harness.queryData.projects = [alfa, beta, gamma];
  });

  afterEach(cleanup);

  it("ilk yuklemede ilk projeyi secer; tarihsiz taslar icin cizelge cizmez", async () => {
    render(<ProjectsPage />);

    expect(await screen.findByRole("heading", { name: "Alfa" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Alfa/ }).getAttribute("aria-current")).toBe("true");
    expect(screen.getByRole("button", { name: /Beta/ }).getAttribute("aria-current")).toBeNull();
    // Alfa'nin tek tasi tarihsiz ve acik -- liste gorur, cizelge cizmez.
    expect(screen.getByText("Alfa adım")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Zaman çizelgesi" })).toBeNull();
  });

  it("liste tiklama ile secim degisir ve milestone zaman cizelgesi gorunur", async () => {
    render(<ProjectsPage />);
    await screen.findByRole("heading", { name: "Alfa" });

    fireEvent.click(screen.getByRole("button", { name: /Beta/ }));

    const timeline = await waitFor(timelineSection);
    expect(screen.getByRole("heading", { name: "Beta" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Beta/ }).getAttribute("aria-current")).toBe("true");
    // Kronolojik gruplar: geciken, yaklasan, tamamlanan, tarihsiz.
    expect(within(timeline).getAllByTestId("milestone-timeline-row")).toHaveLength(4);
    expect(within(timeline).getByText("Geciken")).toBeTruthy();
    expect(within(timeline).getByText("Yaklaşan")).toBeTruthy();
    expect(within(timeline).getByText("Tamamlanan")).toBeTruthy();
    expect(within(timeline).getByText("Tarihsiz")).toBeTruthy();
    expect(within(timeline).getByText("12 gün gecikti")).toBeTruthy();
    expect(within(timeline).getByText("3 gün kaldı")).toBeTruthy();
    // Tamamlananlar cizgili.
    expect(within(timeline).getByText("Beta 3. adım").className).toContain("line-through");
    // Liste hâlâ butun taslari sayar (davranis korundu).
    const list = screen.getByRole("heading", { name: "Kilometre taşları" }).closest("section") as HTMLElement;
    expect(within(list).getByText("1/4")).toBeTruthy();
  });

  it("derin link focus ile secili projeyi acar", async () => {
    harness.focus = "focus=p3";
    render(<ProjectsPage />);

    expect(await screen.findByRole("heading", { name: "Gamma" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Gamma/ }).getAttribute("aria-current")).toBe("true");
    expect(screen.getByRole("button", { name: /Beta/ }).getAttribute("aria-current")).toBeNull();
    expect(screen.queryByRole("heading", { name: "Zaman çizelgesi" })).toBeNull();
  });

  it("secili proje silinince listeye (ilk projeye) doner", async () => {
    harness.focus = "focus=p2";
    const view = render(<ProjectsPage />);
    await screen.findByRole("heading", { name: "Beta" });

    fireEvent.click(screen.getByRole("button", { name: /Projeyi sil/ }));
    await waitFor(() => expect(harness.apiDel).toHaveBeenCalledWith("/projects/p2"));
    expect(harness.invalidate).toHaveBeenCalledWith("project.write");

    // Silme sonrasi liste guncellenir; secili proje yok oldugu icin ilk
    // projeye donulur (derin linkteki id artik listede yok).
    harness.queryData.projects = [alfa, gamma];
    view.rerender(<ProjectsPage />);

    expect(await screen.findByRole("heading", { name: "Alfa" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Beta" })).toBeNull();
    expect(screen.getByRole("button", { name: /Alfa/ }).getAttribute("aria-current")).toBe("true");
  });
});
