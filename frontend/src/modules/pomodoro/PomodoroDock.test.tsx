// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { PomodoroDock } from "./PomodoroDock";
import { openPomodoro } from "./dock";

vi.mock("@/lib/hooks", () => ({
  useOnline: () => true,
  useDebounced: (value: string) => value,
}));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/core/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
  qs: (values: Record<string, string>) => {
    const query = new URLSearchParams(values).toString();
    return query ? `?${query}` : "";
  },
}));

import { api } from "@/core/api";

const apiGet = vi.mocked(api.get);
const apiPost = vi.mocked(api.post);

function renderDock() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <PomodoroDock />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiGet.mockReset();
  apiPost.mockReset();
  apiPost.mockResolvedValue({} as never);
  apiGet.mockImplementation(async (path: string) => {
    if (path === "/pomodoro/active") return null;
    if (path === "/pomodoro/stats?range=day") return { minutes: 0, sessions: 0, interrupted: 0 };
    if (path.startsWith("/pomodoro/contexts")) {
      return [{ id: "topic-42", type: "study_topic", title: "Git Temelleri" }];
    }
    return [];
  });
});

afterEach(cleanup);

describe("global Pomodoro dock", () => {
  it("her sayfada kucuk durur ve istekle baglamli paneli acar", async () => {
    renderDock();
    expect(screen.getByRole("button", { name: "Pomodoro seçeneklerini aç" })).toBeTruthy();

    openPomodoro({ context: "topic-42", topic: "Git Temelleri" });

    expect(await screen.findByRole("dialog", { name: "Pomodoro seçenekleri" })).toBeTruthy();
    expect(screen.getByDisplayValue("Git Temelleri")).toBeTruthy();
    expect(await screen.findByText("study_topic")).toBeTruthy();
  });

  it("secilen baglami odak baslatma istegine tasir", async () => {
    renderDock();
    openPomodoro({ context: "topic-42", topic: "Git Temelleri" });

    fireEvent.click(await screen.findByRole("button", { name: "50 dk odak" }));

    await waitFor(() =>
      expect(apiPost).toHaveBeenCalledWith("/pomodoro/start", {
        planned_min: 50,
        kind: "focus",
        topic: "Git Temelleri",
        context_entity_id: "topic-42",
      }),
    );
  });
});
