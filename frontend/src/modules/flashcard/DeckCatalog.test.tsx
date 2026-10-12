// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "@/core/api";
import { ToastProvider } from "@/core/ui";
import { DeckCatalog } from "./DeckCatalog";
const state = vi.hoisted(() => ({ online: true }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => state.online }));
vi.mock("@/core/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  qs: ({ search }: { search: string }) => `?search=${encodeURIComponent(search)}`,
}));
vi.mock("./invalidate", () => ({ refreshFlashcards: vi.fn() }));
const deck = {
  id: 42,
  title: "İngilizce",
  notes: 2,
  likes: 12,
  has_media: true,
  url: "https://ankiweb.net/shared/info/42",
};
const onOpen = vi.fn();
function show() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <ToastProvider>
        <DeckCatalog onOpen={onOpen} />
      </ToastProvider>
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.clearAllMocks();
  state.online = true;
  vi.mocked(api.get).mockImplementation(async (path) =>
    path.includes("?") ? [deck] : { ...deck, size_bytes: 2000, samples: [["<script>evil()</script>", "cevap"]] },
  );
  vi.mocked(api.post).mockResolvedValue({ deck_id: "new-deck", added: 2 });
});
afterEach(cleanup);
it("previews public content as text and imports only after the user chooses Add", async () => {
  show();
  fireEvent.click(await screen.findByRole("button", { name: "İncele ve ekle" }));
  expect(api.post).not.toHaveBeenCalled();
  expect(await screen.findByText("<script>evil()</script>")).toBeTruthy();
  expect(document.querySelector("script")).toBeNull();
  expect(screen.getByText(/ses ve görseller eklenmez/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Kartlara ekle" }));
  await waitFor(() => expect(onOpen).toHaveBeenCalledWith("new-deck"));
  expect(api.post).toHaveBeenCalledExactlyOnceWith("/flashcard/catalog/42/import", {});
});
it("shows a deliberate retry after catalog failure", async () => {
  vi.mocked(api.get).mockRejectedValueOnce(new Error("AnkiWeb istek sınırı"));
  show();
  fireEvent.click(await screen.findByRole("button", { name: "Yeniden dene" }));
  expect(await screen.findByRole("heading", { name: "İngilizce" })).toBeTruthy();
});
it("does not contact catalog or allow writes offline", () => {
  state.online = false;
  show();
  expect(api.get).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Ara" }).hasAttribute("disabled")).toBe(true);
});
it("opens an AnkiWeb link directly when guest search is unavailable", async () => {
  vi.mocked(api.get).mockRejectedValueOnce(new Error("Misafir arama sınırı"));
  show();
  await screen.findByText("Misafir arama sınırı");
  fireEvent.change(screen.getByRole("textbox", { name: "Deste kataloğunda ara" }), { target: { value: deck.url } });
  fireEvent.click(screen.getByRole("button", { name: "İncele" }));
  await screen.findByText("<script>evil()</script>");
  expect(api.get).toHaveBeenLastCalledWith("/flashcard/catalog/42");
  expect(api.post).not.toHaveBeenCalled();
});
