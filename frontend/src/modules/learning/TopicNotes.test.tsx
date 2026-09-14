// @vitest-environment jsdom
/**
 * TopicNotes — "Konudan ayır" (bag kaldirir) ile "Notu tamamen sil" (entity
 * siler) AYRI aksiyonlar; yanlis aksiyonla global not silinmemeli.
 *
 * Yazma yuzeyi tektir: burada ikinci bir editor acilmaz, "Not al" notu konuya
 * baglar ve Notlar modulunde acar; "Notu duzenle" de ayni yere gider.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DialogHost } from "@/core/dialog";
import { ToastProvider } from "@/core/ui";
import { TopicNotes } from "./TopicNotes";

const harness = vi.hoisted(() => ({
  apiDel: vi.fn(),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
}));

vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return { ...actual, api: { del: harness.apiDel, get: harness.apiGet, post: harness.apiPost } };
});
vi.mock("@/core/invalidation", () => ({ invalidateAfter: (...events: string[]) => harness.invalidate(...events) }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true, useDebounced: <T,>(value: T) => value }));

const notes = [
  {
    id: "n1",
    title: "Git notları",
    body: "Commit atmadan önce [[Branch Yönetimi]] oku. #git",
    pinned: false,
    created_at: "2026-09-01T08:00:00Z",
    updated_at: "2026-09-09T08:00:00Z",
    tags: ["git"],
    resolved_links: [],
    unresolved_links: [],
    attachments: [],
  },
  {
    id: "n2",
    title: "Alıştırma notu",
    body: "Alıştırmayı bitir. #pratik",
    pinned: false,
    created_at: "2026-09-02T08:00:00Z",
    updated_at: "2026-09-08T08:00:00Z",
    tags: ["pratik"],
    resolved_links: [],
    unresolved_links: [],
    attachments: [],
  },
];

function renderNotes() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <DialogHost />
        <TopicNotes topicId="t1" noteCount={2} />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("TopicNotes", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.apiDel.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.apiGet.mockResolvedValue(notes);
    location.hash = "";
  });

  afterEach(cleanup);

  it("notlari konuya bagli olarak listeler ve sayaci gosterir", async () => {
    renderNotes();
    expect(await screen.findByText("Git notları")).toBeTruthy();
    expect(screen.getByText("2 not")).toBeTruthy();
    expect(harness.apiGet).toHaveBeenCalledWith("/notes?about=t1");
  });

  it("'Konudan ayır' yalnizca notes_about bagini kaldirir; not SILINMEZ", async () => {
    renderNotes();
    fireEvent.click((await screen.findAllByRole("button", { name: "Konudan ayır (not silinmez)" }))[0]);
    const dialog = await screen.findByRole("alertdialog");
    expect(within(dialog).getByText(/Not silinmez/)).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("button", { name: "Konudan ayır" }));

    await waitFor(() =>
      expect(harness.apiDel).toHaveBeenCalledWith("/links", {
        from_id: "n1",
        to_id: "t1",
        relation: "notes_about",
      }),
    );
    // Entity silme cagrisi YOK.
    expect(harness.apiDel).not.toHaveBeenCalledWith("/notes/n1");
    expect(harness.invalidate).toHaveBeenCalledWith("link.write", "note.write");
    expect(screen.getByText("Git notları")).toBeTruthy();
  });

  it("'Notu tamamen sil' entity'yi siler ve sistemden silinecegini acikca soyler", async () => {
    renderNotes();
    fireEvent.click((await screen.findAllByRole("button", { name: "Notu tamamen sil" }))[0]);
    const dialog = await screen.findByRole("alertdialog");
    expect(within(dialog).getByText(/sistemden silinecek/)).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("button", { name: "Notu tamamen sil" }));

    await waitFor(() => expect(harness.apiDel).toHaveBeenCalledWith("/notes/n1"));
    expect(harness.apiDel).not.toHaveBeenCalledWith("/links", expect.anything());
    expect(harness.invalidate).toHaveBeenCalledWith("note.write");
  });

  it("etiket tiklamasi listeyi suzer, ikinci tiklama filtreyi kaldirir", async () => {
    renderNotes();
    fireEvent.click((await screen.findAllByRole("button", { name: "#git" }))[0]);
    expect(screen.getByText("Git notları")).toBeTruthy();
    expect(screen.queryByText("Alıştırma notu")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Etiket filtresini temizle" }));
    expect(screen.getByText("Alıştırma notu")).toBeTruthy();
  });

  it("'Not al' notu konuya baglar ve tam editoru acar", async () => {
    harness.apiPost.mockResolvedValue({ ...notes[0], id: "n9" });
    renderNotes();

    fireEvent.click(await screen.findByRole("button", { name: /Not al/ }));
    const dialog = await screen.findByRole("dialog", { name: "Yeni not" });
    fireEvent.change(within(dialog).getByLabelText("Not başlığı"), { target: { value: "Türev notları" } });
    fireEvent.change(within(dialog).getByLabelText("İlk satır"), { target: { value: "Zincir kuralı" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Notu oluştur ve aç" }));

    await waitFor(() =>
      expect(harness.apiPost).toHaveBeenCalledWith("/notes", {
        body: "Türev notları\n\nZincir kuralı",
        relate_to: "t1",
      }),
    );
    await waitFor(() => expect(location.hash).toContain("/notes?focus=n9"));
    expect(harness.invalidate).toHaveBeenCalledWith("note.write");
  });

  it("bos besteciyle not olusturulmaz", async () => {
    renderNotes();
    fireEvent.click(await screen.findByRole("button", { name: /Not al/ }));
    const dialog = await screen.findByRole("dialog", { name: "Yeni not" });

    const submit = within(dialog).getByRole("button", { name: "Notu oluştur ve aç" }) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
    fireEvent.click(submit);
    expect(harness.apiPost).not.toHaveBeenCalled();
    expect(location.hash).not.toContain("/notes");
  });

  it("'Notu duzenle' satir ici editor yerine Notlar sayfasini acar", async () => {
    renderNotes();
    fireEvent.click((await screen.findAllByRole("button", { name: "Notu düzenle (Notlar sayfasında)" }))[0]);

    await waitFor(() => expect(location.hash).toContain("/notes?focus=n1"));
    // Satir ici ikinci editor YOK.
    expect(screen.queryByRole("button", { name: /Kaydet/ })).toBeNull();
  });

  it("dis aksiyon sinyali besteciyi acar", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const view = (signal: number) => (
      <QueryClientProvider client={client}>
        <TopicNotes topicId="t1" composeSignal={signal} />
      </QueryClientProvider>
    );
    const { rerender } = render(view(0));
    await screen.findByText("Git notları");
    expect(screen.queryByText("Yeni not")).toBeNull();

    rerender(view(1));
    expect(await screen.findByRole("dialog", { name: "Yeni not" })).toBeTruthy();
  });

  it("vazgecince hicbir silme cagrisi gitmez", async () => {
    renderNotes();
    fireEvent.click((await screen.findAllByRole("button", { name: "Notu tamamen sil" }))[0]);
    const dialog = await screen.findByRole("alertdialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Vazgeç" }));
    expect(harness.apiDel).not.toHaveBeenCalled();
  });
});
