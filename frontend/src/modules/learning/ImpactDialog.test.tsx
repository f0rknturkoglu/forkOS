// @vitest-environment jsdom
/**
 * ImpactDialog — silme oncesi etki sayilari ve onayli DELETE.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { ImpactDialog } from "./ImpactDialog";

const harness = vi.hoisted(() => ({
  apiDel: vi.fn(),
  apiGet: vi.fn(),
  invalidate: vi.fn(),
}));

vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return { ...actual, api: { del: harness.apiDel, get: harness.apiGet } };
});
vi.mock("@/core/invalidation", () => ({ invalidateAfter: (...events: string[]) => harness.invalidate(...events) }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));

function renderDialog(onDeleted = vi.fn(), onClose = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <ImpactDialog topicId="t1" topicTitle=".gitignore" open onClose={onClose} onDeleted={onDeleted} />
      </ToastProvider>
    </QueryClientProvider>,
  );
  return { onDeleted, onClose };
}

describe("ImpactDialog", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.apiDel.mockReset();
    harness.invalidate.mockReset();
    harness.apiGet.mockResolvedValue({ topics: 3, resources: 1, links: 1, plan_slots: 0, todos: 2, notes: 0 });
    harness.apiDel.mockResolvedValue(undefined);
  });

  afterEach(cleanup);

  it("etki sayilarini gosterir", async () => {
    renderDialog();
    expect(await screen.findByText("Konu (alt konular dahil)")).toBeTruthy();
    expect(harness.apiGet).toHaveBeenCalledWith("/study/topics/t1/impact");
    const rows = [
      ["Konu (alt konular dahil)", "3"],
      ["Kaynak", "1"],
      ["Bağlantı", "1"],
      ["Plan kaydı", "0"],
      ["Görev", "2"],
      ["Not", "0"],
    ] as const;
    for (const [label, value] of rows) {
      const row = screen.getByText(label).closest("div");
      expect(within(row as HTMLElement).getByText(value)).toBeTruthy();
    }
  });

  it("onay sonrasi DELETE atar, study.write tazeler ve onDeleted cagirir", async () => {
    const { onDeleted } = renderDialog();
    fireEvent.click(await screen.findByRole("button", { name: /Konuyu sil/ }));
    await waitFor(() => expect(harness.apiDel).toHaveBeenCalledWith("/study/topics/t1"));
    expect(harness.invalidate).toHaveBeenCalledWith("study.write");
    expect(onDeleted).toHaveBeenCalled();
  });

  it("etki alinamazsa hata bildirir ve silme denenmez", async () => {
    harness.apiGet.mockRejectedValue(new Error("offline"));
    renderDialog();
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Silme etkisi alınamadı");
    expect(harness.apiDel).not.toHaveBeenCalled();
  });
});
