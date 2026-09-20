// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Project } from "@/core/types";
import { ProjectKnowledgeNote } from "./ProjectKnowledgeNote";

const harness = vi.hoisted(() => ({
  status: null as unknown,
  item: null as unknown,
  createItem: vi.fn(),
  toast: vi.fn(),
}));

vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/ui")>();
  return {
    ...actual,
    useToast: () => ({ push: harness.toast }),
  };
});

vi.mock("@/core/obsidian", () => ({
  getVaultStatus: () => Promise.resolve(harness.status),
  getVaultItem: () => (harness.item ? Promise.resolve(harness.item) : Promise.reject(new Error("Not found"))),
  createVaultItem: (args: unknown) => harness.createItem(args),
}));

vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery: vi.fn((options: { queryKey: readonly unknown[]; enabled?: boolean }) => {
      const key = String(options.queryKey[0]);
      if (key === "obsidian-status") {
        return { data: harness.status, isLoading: false };
      }
      if (key === "obsidian-item") {
        if (options.enabled === false) return { data: undefined, isLoading: false };
        return { data: harness.item, isLoading: false };
      }
      return { data: undefined, isLoading: false };
    }),
    useMutation: vi.fn((options: { mutationFn: () => Promise<unknown>; onSuccess?: (data: unknown) => void }) => ({
      mutate: async () => {
        const result = await options.mutationFn();
        options.onSuccess?.(result);
      },
      isPending: false,
    })),
  };
});

const mockProject: Project = {
  id: "p1111111-1111-1111-1111-111111111111",
  title: "forkOS Core",
  status: "active",
  github_repo: "f0rknturkoglu/forkOS",
  url: null,
  stack: ["python", "react"],
  next_action: null,
  last_activity_at: null,
  position: 0,
  milestones: [],
};

describe("ProjectKnowledgeNote", () => {
  beforeEach(() => {
    harness.status = { configured: true, available: true, writable: true, vault_name: "Vault" };
    harness.item = null;
    harness.createItem.mockReset();
    harness.toast.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("Vault yapılandırılmamışsa bilgilendirme metni gösterir", () => {
    harness.status = { configured: false, available: false, writable: false, vault_name: "Vault" };
    render(<ProjectKnowledgeNote project={mockProject} />);
    expect(screen.getByText(/Obsidian Vault yapılandırılmamış/)).toBeDefined();
  });

  it("Not mevcutsa başlığını, yolunu ve açma bağlantısını listeler", () => {
    harness.item = {
      forkos_id: mockProject.id,
      forkos_type: "project",
      title: "forkOS Core",
      relative_path: "20 Projects/forkOS Core.md",
      open_uri: "obsidian://open?vault=Vault&file=20%20Projects%2FforkOS%20Core",
      mtime: 12345,
      size: 100,
    };
    render(<ProjectKnowledgeNote project={mockProject} />);
    expect(screen.getByText("forkOS Core")).toBeDefined();
    expect(screen.getByText("20 Projects/forkOS Core.md")).toBeDefined();
    const link = screen.getByRole("link", { name: /Obsidian'da aç/i });
    expect(link.getAttribute("href")).toBe("obsidian://open?vault=Vault&file=20%20Projects%2FforkOS%20Core");
  });

  it("Not henüz bağlanmamışsa oluşturma butonu sunar ve tıklandığında oluşturur", async () => {
    harness.item = null;
    const createdItem = {
      forkos_id: mockProject.id,
      forkos_type: "project",
      title: "forkOS Core",
      relative_path: "20 Projects/forkOS Core.md",
      open_uri: "obsidian://open?vault=Vault&file=20%20Projects%2FforkOS%20Core",
    };
    harness.createItem.mockResolvedValue(createdItem);

    render(<ProjectKnowledgeNote project={mockProject} />);
    const btn = screen.getByRole("button", { name: /Obsidian proje notu oluştur/i });
    expect(btn).toBeDefined();

    fireEvent.click(btn);
    await waitFor(() => {
      expect(harness.createItem).toHaveBeenCalledWith({
        forkos_id: mockProject.id,
        forkos_type: "project",
        title: "forkOS Core",
        target_folder: "20 Projects",
      });
    });
  });

  it("Kimlik çakışması (duplicate conflict) varsa uyarı gösterir ve oluştur butonunu gizler", () => {
    harness.status = {
      configured: true,
      available: true,
      writable: true,
      vault_name: "Vault",
      conflicts: 1,
      conflict_details: {
        [mockProject.id]: [
          "20 Projects/forkOS Core/forkOS Core.md",
          "20 Projects/Old/forkOS Core.md",
        ],
      },
    };
    harness.item = null;

    render(<ProjectKnowledgeNote project={mockProject} />);
    expect(
      screen.getByText(/Bu kimlik birden fazla Obsidian dosyasında kullanılıyor/i)
    ).toBeDefined();
    expect(screen.getByText("20 Projects/forkOS Core/forkOS Core.md")).toBeDefined();
    expect(screen.getByText("20 Projects/Old/forkOS Core.md")).toBeDefined();

    const btn = screen.queryByRole("button", { name: /Obsidian proje notu oluştur/i });
    expect(btn).toBeNull();
  });
});
