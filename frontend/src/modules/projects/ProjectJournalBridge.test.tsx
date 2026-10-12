// @vitest-environment jsdom
/**
 * ProjectJournalBridge — gunluk notunun Vault koprusu.
 *
 * Kabul kriterleri: POST hedefi `/projects/{id}/journal/{day}/obsidian`,
 * donen `open_uri` isletim sistemine devredilir, Vault yazmasi
 * `obsidian.write` bildirir, gelecek gun UI'da reddedilir ve Vault kapaliysa
 * hata uretecek aksiyon yerine "Vault kullanılamıyor" bilgisi cikar.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { ToastProvider } from "@/core/ui";
import { todayKey } from "@/lib/date";
import { ProjectJournalBridge } from "./ProjectJournalBridge";

const harness = vi.hoisted(() => ({
  status: null as unknown,
  apiPost: vi.fn(),
  open: vi.fn(),
}));

vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/obsidian", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/obsidian")>();
  return {
    ...actual,
    getVaultStatus: () => Promise.resolve(harness.status),
    openObsidianUri: (uri: string) => harness.open(uri),
  };
});
vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return { ...actual, api: { post: harness.apiPost } };
});

function journalItem(day: string) {
  return {
    forkos_id: "project-1",
    forkos_type: "project",
    title: "forkOS Core · Günlük",
    relative_path: `10 Journals/forkOS Core/${day}.md`,
    open_uri: `obsidian://open?vault=Vault&file=10%20Journals%2FforkOS%20Core%2F${day}`,
    mtime: 1,
    size: 1,
    note_kind: "journal",
    entity_type: "project",
    project_id: "project-1",
    journal_day: day,
    source_bookmark_id: null,
    relation_count: 0,
  };
}

function renderBridge() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <ProjectJournalBridge projectId="project-1" />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("ProjectJournalBridge", () => {
  beforeEach(() => {
    harness.status = { configured: true, available: true, writable: true, vault_name: "Vault" };
    harness.apiPost.mockReset();
    harness.open.mockReset();
    vi.mocked(invalidateAfter).mockReset();
  });

  afterEach(cleanup);

  it("bugunun gunlugunu dogru hedefe POST eder, notu acar ve Vault'u tazeler", async () => {
    harness.apiPost.mockResolvedValue(journalItem(todayKey()));
    renderBridge();

    fireEvent.click(await screen.findByRole("button", { name: /Bugünü Obsidian’da aç/i }));

    await waitFor(() =>
      expect(harness.apiPost).toHaveBeenCalledWith(`/projects/project-1/journal/${todayKey()}/obsidian`, {}),
    );
    expect(harness.open).toHaveBeenCalledWith(journalItem(todayKey()).open_uri);
    expect(invalidateAfter).toHaveBeenCalledWith("obsidian.write");
  });

  it("gecmis gun secilince o gunun hedefine POST eder", async () => {
    const past = "2026-01-05";
    harness.apiPost.mockResolvedValue(journalItem(past));
    renderBridge();

    const day = (await screen.findByLabelText("Günlük günü")) as HTMLInputElement;
    expect(day.value).toBe(todayKey());
    fireEvent.change(day, { target: { value: past } });
    fireEvent.click(screen.getByRole("button", { name: /Bu günü Obsidian’da aç/i }));

    await waitFor(() =>
      expect(harness.apiPost).toHaveBeenCalledWith(`/projects/project-1/journal/${past}/obsidian`, {}),
    );
    expect(harness.open).toHaveBeenCalledWith(journalItem(past).open_uri);
  });

  it("gelecek gun secilemez; POST atilmaz", async () => {
    renderBridge();
    const day = (await screen.findByLabelText("Günlük günü")) as HTMLInputElement;

    const future = "2099-01-01";
    fireEvent.change(day, { target: { value: future } });

    expect(day.value).toBe(todayKey());
    fireEvent.click(screen.getByRole("button", { name: /Obsidian’da aç/i }));
    await waitFor(() => expect(harness.apiPost).toHaveBeenCalledTimes(0));
  });

  it("Vault kapaliysa aksiyon yerine 'Vault kullanılamıyor' bilgisi gosterir", async () => {
    harness.status = { configured: false, available: false, writable: false, vault_name: "Vault" };
    renderBridge();

    expect(await screen.findByText(/Vault kullanılamıyor/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Obsidian’da aç/i })).toBeNull();
    expect(screen.queryByLabelText("Günlük günü")).toBeNull();
  });

  it("sunucu reddederse hata bildirir ve notu acmaz", async () => {
    harness.apiPost.mockRejectedValue(new ApiError(400, "Gelecek bir gun icin gunluk notu yazilamaz", null));
    renderBridge();

    fireEvent.click(await screen.findByRole("button", { name: /Bugünü Obsidian’da aç/i }));

    expect(await screen.findByText(/Proje günlüğü açılamadı/)).toBeTruthy();
    expect(harness.open).not.toHaveBeenCalled();
    expect(invalidateAfter).not.toHaveBeenCalled();
  });
});
