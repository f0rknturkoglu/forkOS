// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NoteSidebarTree } from "./NoteSidebarTree";

vi.mock("@/app/router", () => ({ useHashRoute: () => ({ params: new URLSearchParams("focus=n2") }) }));
vi.mock("@/core/api", () => ({
  api: {
    get: vi.fn(async (path: string) => {
      if (path === "/note-folders")
        return [
          { id: "f1", name: "Araştırma", parent_id: null, position: 0, note_count: 1, created_at: "", updated_at: "" },
        ];
      if (path === "/projects") return [];
      if (path === "/notes")
        return [
          {
            id: "n1",
            title: "Kök not",
            body: "",
            pinned: false,
            folder_id: null,
            created_at: "2026-09-04T00:00:00Z",
            updated_at: "2026-09-04T00:00:00Z",
          },
          {
            id: "n2",
            title: "Klasörlü not",
            body: "",
            pinned: false,
            folder_id: "f1",
            created_at: "2026-09-04T00:00:00Z",
            updated_at: "2026-09-04T00:00:00Z",
          },
        ];
      return [];
    }),
    post: vi.fn(),
    patch: vi.fn(),
    del: vi.fn(),
  },
}));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));

afterEach(cleanup);

describe("NoteSidebarTree", () => {
  it("klasörleri ve kök notları ana sidebar altında gruplar", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <NoteSidebarTree collapsed={false} onNavigate={vi.fn()} />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Araştırma")).toBeTruthy();
    expect(screen.getByText("Klasörlü not")).toBeTruthy();
    expect(screen.getByText("Kök not")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Araştırma klasörünü daralt" }));
    expect(screen.queryByText("Klasörlü not")).toBeNull();
  });
});
