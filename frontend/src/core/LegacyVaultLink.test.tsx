// @vitest-environment jsdom
import { cleanup, render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./api";
import { LegacyVaultLink } from "./LegacyVaultLink";

const mocks = vi.hoisted(() => ({ focus: "", getItem: vi.fn(), open: vi.fn(), navigate: vi.fn() }));
vi.mock("@/app/router", () => ({
  useHashRoute: () => ({ params: new URLSearchParams(mocks.focus ? { focus: mocks.focus } : {}) }),
  navigate: mocks.navigate,
}));
vi.mock("./obsidian", () => ({
  getVaultItem: mocks.getItem,
  openObsidianUri: mocks.open,
  VAULT_ITEM_KEY: "vault-item",
}));
function mount() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <LegacyVaultLink />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.clearAllMocks();
  mocks.focus = "d4050e09-428b-43ea-b76d-4fe872975b47";
});
afterEach(cleanup);
describe("legacy Vault links", () => {
  it("resolves the identifier and opens the returned URI once without navigating", async () => {
    mocks.getItem.mockResolvedValue({ title: "Fixture", open_uri: "obsidian://open?vault=Fixture&file=note" });
    const view = mount();
    await screen.findByText(/Obsidian'a gönderildi/);
    expect(mocks.getItem).toHaveBeenCalledWith(mocks.focus);
    expect(mocks.open).toHaveBeenCalledTimes(1);
    view.rerender(
      <QueryClientProvider client={new QueryClient()}>
        <LegacyVaultLink />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(mocks.open).toHaveBeenCalledTimes(1));
    expect(mocks.navigate).not.toHaveBeenCalled();
  });
  it("redirects links without an identifier to Vault settings", async () => {
    mocks.focus = "";
    mount();
    await waitFor(() => expect(mocks.navigate).toHaveBeenCalledWith("/settings?tab=brain", { replace: true }));
    expect(mocks.getItem).not.toHaveBeenCalled();
  });
  it("rejects malformed identifiers without issuing a lookup", () => {
    mocks.focus = "bad";
    mount();
    expect(screen.getByRole("alert").textContent).toContain("geçersiz");
    expect(mocks.getItem).not.toHaveBeenCalled();
  });
  it.each([
    [404, "Not bulunamadı"],
    [503, "Vault erişilemiyor"],
    [409, "Kimlik çakışması"],
  ])("preserves lookup failure %i and offers retry/settings", async (status, message) => {
    mocks.getItem.mockRejectedValue(new ApiError(status, message));
    mount();
    expect((await screen.findByRole("alert")).textContent).toContain(message);
    expect(mocks.open).not.toHaveBeenCalled();
    expect(mocks.navigate).not.toHaveBeenCalled();
    mocks.getItem.mockResolvedValue({ title: "Recovered", open_uri: "obsidian://open?vault=Fixture" });
    fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
    await screen.findByText(/Recovered/);
    expect(mocks.open).toHaveBeenCalledTimes(1);
  });
});
