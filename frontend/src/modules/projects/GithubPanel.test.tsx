// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { GithubRepoPanel, Project } from "@/core/types";
import { GithubPanel, githubPanelError } from "./GithubPanel";

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  online: true,
}));

vi.mock("@/core/api", () => ({
  api: { get: harness.apiGet, post: harness.apiPost },
}));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/lib/hooks", () => ({
  useOnline: () => harness.online,
}));

const project = {
  id: "project-1",
  title: "forkOS",
  github_repo: "owner/repo",
  milestones: [],
} as unknown as Project;

const panel: GithubRepoPanel = {
  repo: "owner/repo",
  url: "https://github.com/owner/repo",
  description: "Local life operating system",
  stars: 3,
  forks: 1,
  watchers: 2,
  language: "TypeScript",
  open_issues: 2,
  default_branch: "main",
  pushed_at: "2026-08-29T11:00:00Z",
  fetched_at: "2026-08-29T11:01:00Z",
  private: true,
  authenticated: true,
  issues: [
    {
      number: 17,
      title: "Older issue",
      url: "https://github.com/owner/repo/issues/17",
      state: "open",
      labels: ["bug"],
      assignee: null,
      comments: 2,
      created_at: "2026-08-28T08:00:00Z",
      updated_at: "2026-08-29T08:00:00Z",
      author: "owner",
      draft: false,
      todo_id: null,
    },
    {
      number: 18,
      title: "Converted issue",
      url: "https://github.com/owner/repo/issues/18",
      state: "open",
      labels: [],
      assignee: null,
      comments: 0,
      created_at: "2026-08-27T08:00:00Z",
      updated_at: "2026-08-28T08:00:00Z",
      author: "owner",
      draft: false,
      todo_id: "todo-18",
    },
  ],
  pulls: [
    {
      number: 21,
      title: "Open pull request",
      url: "https://github.com/owner/repo/pull/21",
      state: "open",
      labels: [],
      assignee: null,
      comments: 1,
      created_at: "2026-08-29T08:30:00Z",
      updated_at: "2026-08-29T09:00:00Z",
      author: "contributor",
      draft: false,
      todo_id: null,
    },
  ],
  commits: [
    {
      sha: "abcdef1",
      message: "Newest commit",
      url: "https://github.com/owner/repo/commit/abcdef1",
      author: "owner",
      committed_at: "2026-08-29T10:00:00Z",
    },
  ],
};

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <GithubPanel project={project} />
    </QueryClientProvider>,
  );
}

describe("project GitHub hub", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.online = true;
    harness.apiGet.mockResolvedValue(panel);
    harness.apiPost.mockResolvedValue({ duplicate: false, id: "todo-17", title: "Older issue" });
  });

  afterEach(cleanup);

  it("opens on a chronological all-activity stream instead of an empty-prone tab", async () => {
    renderPanel();

    const all = await screen.findByRole("button", { name: /Tümü/ });
    expect(all.getAttribute("aria-pressed")).toBe("true");
    const rows = screen.getAllByTestId("github-activity-row");
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringContaining("Newest commit"),
      expect.stringContaining("Open pull request"),
      expect.stringContaining("Older issue"),
      expect.stringContaining("Converted issue"),
    ]);
  });

  it("filters the unified stream and keeps commits visible when issues are absent", async () => {
    renderPanel();
    await screen.findByText("Newest commit");

    fireEvent.click(screen.getByRole("button", { name: /Commit 1/ }));
    expect(screen.getByText("Newest commit")).toBeTruthy();
    expect(screen.queryByText("Older issue")).toBeNull();
    expect(screen.queryByText("Open pull request")).toBeNull();
  });

  it("shows persisted todo state and only blocks the issue being converted", async () => {
    let resolvePost: ((value: unknown) => void) | undefined;
    harness.apiPost.mockReturnValue(new Promise((resolve) => (resolvePost = resolve)));
    renderPanel();

    expect(await screen.findByText("Görevlerde")).toBeTruthy();
    const row = screen.getByText("Older issue").closest("li");
    const create = within(row as HTMLElement).getByRole("button", { name: "Göreve dönüştür" });
    fireEvent.click(create);

    await waitFor(() => expect((create as HTMLButtonElement).disabled).toBe(true));
    expect(screen.getByText("Görevlerde")).toBeTruthy();
    expect(harness.apiPost).toHaveBeenCalledWith("/projects/project-1/github/issues", { number: 17 });

    resolvePost?.({ duplicate: false, id: "todo-17", title: "Older issue" });
    await waitFor(() => expect(harness.invalidate).toHaveBeenCalledWith("project.write"));
  });

  it("forces backend refresh and reports GitHub fetch freshness", async () => {
    renderPanel();

    expect(await screen.findByText(/GitHub'dan .* alındı/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "GitHub verisini yenile" }));

    await waitFor(() => expect(harness.apiGet).toHaveBeenCalledWith("/projects/project-1/github?refresh=true"));
  });

  it("keeps cached content while a manual refresh fails and hides raw errors", async () => {
    harness.apiGet.mockImplementation((path: string) =>
      path.includes("refresh=true")
        ? Promise.reject(new Error('{"detail":"GitHub 404: Not Found"}'))
        : Promise.resolve(panel),
    );
    renderPanel();

    await screen.findByText("Newest commit");
    fireEvent.click(screen.getByRole("button", { name: "GitHub verisini yenile" }));

    expect(await screen.findByText("Depo bulunamadı veya erişim izni yok.")).toBeTruthy();
    expect(screen.getByText("Newest commit")).toBeTruthy();
    expect(screen.queryByText(/Not Found/)).toBeNull();
  });

  it.each([
    ["GitHub 401: Bad credentials", "GitHub bağlantısı geçersiz.", true],
    ["GitHub 403: API rate limit exceeded", "GitHub istek sınırına ulaşıldı.", false],
    ["GitHub 403: Resource not accessible", "GitHub bu depoya erişime izin vermedi.", true],
  ])("classifies actionable GitHub failures without leaking raw details", (message, title, settings) => {
    expect(githubPanelError(new Error(message))).toEqual(expect.objectContaining({ title, settings }));
  });

  it("renders a structure-shaped loading state", () => {
    harness.apiGet.mockReturnValue(new Promise(() => undefined));
    renderPanel();

    expect(screen.getByRole("status", { name: "GitHub verisi yükleniyor" })).toBeTruthy();
  });

  it("retains readable data offline and disables network actions", async () => {
    harness.online = false;
    renderPanel();

    expect(await screen.findByText("Newest commit")).toBeTruthy();
    expect((screen.getByRole("button", { name: "GitHub verisini yenile" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/çevrimdışı/i)).toBeTruthy();
  });

  it("header ozet satiri depo istatistiklerini ve haftalik commit sayisini gosterir", async () => {
    const recent = Array.from({ length: 2 }, (_, index) => ({
      sha: `week${index}`,
      message: `Weekly commit ${index}`,
      url: `https://github.com/owner/repo/commit/week${index}`,
      author: "owner",
      committed_at: new Date(Date.now() - index * 86_400_000).toISOString(),
    }));
    harness.apiGet.mockResolvedValue({ ...panel, commits: recent });
    renderPanel();

    const line = await screen.findByTestId("github-repo-stats");
    expect(line.textContent).toContain("TypeScript");
    expect(line.textContent).toContain("issue");
    expect(line.textContent).toContain("son push");
    expect(line.textContent).toContain("bu hafta 2 commit");
  });

  it("10 commit ile sinirli listede pencere dolunca '10+' gosterir", async () => {
    const saturated = Array.from({ length: 10 }, (_, index) => ({
      sha: `sat${index}`,
      message: `Saturated commit ${index}`,
      url: `https://github.com/owner/repo/commit/sat${index}`,
      author: "owner",
      committed_at: new Date(Date.now() - index * 3_600_000).toISOString(),
    }));
    harness.apiGet.mockResolvedValue({ ...panel, commits: saturated });
    renderPanel();

    const line = await screen.findByTestId("github-repo-stats");
    expect(line.textContent).toContain("bu hafta 10+ commit");
  });
});
