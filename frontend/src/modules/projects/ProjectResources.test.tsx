// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "@/core/api";
import { ProjectResources } from "./ProjectResources";
import type { Project } from "@/core/types";

vi.mock("@/core/api", () => ({ api: { get: vi.fn(), post: vi.fn(), del: vi.fn() } }));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
const project = { id: "p1", title: "Project", milestones: [] } as unknown as Project;
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

it("retries a lost resource response with the same identity and clears only after success", async () => {
  vi.mocked(api.get).mockResolvedValue([]);
  vi.mocked(api.post).mockRejectedValueOnce(new Error("lost response")).mockResolvedValueOnce({});
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ProjectResources project={project} editing />
    </QueryClientProvider>,
  );
  fireEvent.change(screen.getByLabelText("Bağlantı adı"), { target: { value: "Doküman" } });
  fireEvent.change(screen.getByLabelText("Bağlantı adresi"), { target: { value: "example.com/doc" } });
  fireEvent.click(screen.getByRole("button", { name: "Bağlantı ekle" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Bağlantı ekle" }).hasAttribute("disabled")).toBe(false),
  );
  const original = vi.mocked(api.post).mock.calls[0][1];
  expect(original).toMatchObject({ title: "Doküman", url: "https://example.com/doc", client_uuid: expect.any(String) });
  fireEvent.click(screen.getByRole("button", { name: "Bağlantı ekle" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.post).mock.calls[1][1]).toEqual(original);
  await waitFor(() => expect((screen.getByLabelText("Bağlantı adı") as HTMLInputElement).value).toBe(""));
  client.clear();
});
