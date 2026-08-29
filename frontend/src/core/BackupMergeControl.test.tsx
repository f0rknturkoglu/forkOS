// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BackupMergeControl } from "./BackupMergeControl";

type MutationOptions = {
  mutationKey?: readonly unknown[];
  mutationFn?: (variables: never) => Promise<unknown> | unknown;
  onSuccess?: (result: unknown) => void;
};

const harness = vi.hoisted(() => ({
  apiUpload: vi.fn(),
  invalidate: vi.fn(),
  confirm: vi.fn(),
  inspectResult: {} as Record<string, unknown>,
  mergeResult: {} as Record<string, unknown>,
  mutations: [] as MutationOptions[],
}));

vi.mock("@/core/api", () => ({ api: { upload: harness.apiUpload } }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/core/dialog", () => ({
  confirmDialog: (options: { confirmLabel?: string }) => {
    harness.confirm(options.confirmLabel);
    return Promise.resolve(true);
  },
}));
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn((options: MutationOptions) => {
    harness.mutations.push(options);
    return {
      isPending: false,
      mutate: (variables: never) => {
        void options.mutationFn?.(variables);
        const key = String(options.mutationKey?.[0]);
        options.onSuccess?.(key === "backup-inspect" ? harness.inspectResult : harness.mergeResult);
      },
    };
  }),
}));

const file = new File(["{}"], "yedek.json", { type: "application/json" });

function pickFile() {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  fireEvent.change(input, { target: { files: [file] } });
}

describe("BackupMergeControl (Faz 16)", () => {
  beforeEach(() => {
    harness.apiUpload.mockReset();
    harness.invalidate.mockReset();
    harness.confirm.mockReset();
    harness.mutations.length = 0;
    harness.inspectResult = {
      version: 2,
      app: "forkos",
      exported_at: "2026-08-29T00:00:00Z",
      table_counts: { entities: 3, links: 2, events: 5, modules: { todo: 3 } },
      unknown_tables: [],
      missing_sections: [],
      secret_settings: 0,
      integrity_ok: true,
    };
    harness.mergeResult = { restored: 3, skipped: 1, tables: { todo: { inserted: 3, skipped: 1 } } };
  });
  afterEach(() => cleanup());

  it("once preflight cagirir, raporu gosterir, sonra merge eder", async () => {
    render(<BackupMergeControl />);

    // Dosya sec -> inspect (yazma YOK).
    pickFile();
    expect(harness.apiUpload).toHaveBeenCalledWith("/backup/inspect", file);
    expect(screen.getByText(/Dosya incelendi/)).toBeTruthy();
    expect(screen.getByText(/Format v2 \(forkos\) · 3 entity · 2 link · 5 event/)).toBeTruthy();

    // Onay -> merge import (confirmDialog await'i microtask'te doner).
    fireEvent.click(screen.getByRole("button", { name: "Evet, birleştir" }));
    await waitFor(() => expect(harness.confirm).toHaveBeenCalledWith("Birleştirerek içe aktar"));
    await waitFor(() => expect(harness.apiUpload).toHaveBeenCalledWith("/backup/restore", file));
    expect(harness.invalidate).toHaveBeenCalledWith("backup.write");
  });

  it("secret satirlari ve butunluk bozuklugunu raporlar; butunluk bozuksa kilitlenir", () => {
    harness.inspectResult = {
      ...harness.inspectResult,
      secret_settings: 2,
      integrity_ok: false,
      unknown_tables: ["mystery"],
    } as Record<string, unknown>;
    render(<BackupMergeControl />);
    pickFile();

    expect(screen.getByText(/2 secret ayar içeri alınmayacak/)).toBeTruthy();
    expect(screen.getByText(/Bilinmeyen tablolar yok sayılacak: mystery/)).toBeTruthy();
    expect(screen.getByText(/Bütünlük bozuk/)).toBeTruthy();
    const merge = screen.getByRole("button", { name: "Evet, birleştir" }) as HTMLButtonElement;
    expect(merge.disabled).toBe(true);
  });
});
