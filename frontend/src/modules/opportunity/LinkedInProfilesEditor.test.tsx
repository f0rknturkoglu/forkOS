// @vitest-environment jsdom
/**
 * LinkedInProfilesEditor — paylaşılan LinkedIn arama profili editörü.
 *
 * Kapsam: sunucudan gelen profiller, ekle/düzenle/sil akışıyla birlikte
 * `PUT /sources/forkjob-core/linkedin-profiles` gövdesine eksiksiz yazılır ve
 * çevrimdışıyken kaydetme kapalıdır.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type * as UiModule from "@/core/ui";

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
}));

vi.mock("@/core/api", () => ({ api: apiMock, qs: () => "" }));
vi.mock("@/core/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof UiModule>();
  return { ...actual, useToast: () => ({ push: vi.fn() }) };
});

import { LinkedInProfilesEditor } from "./LinkedInProfilesEditor";

/** Sunucudaki mevcut profil; UI'da düzenlenmeyen alanlar da korunmalı. */
const STORED = [
  {
    term: "Frontend",
    location: "Berlin",
    results_wanted: 25,
    hours_old: 72,
    fetch_description: true,
    is_remote: true,
  },
];

function renderEditor(online = true) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <LinkedInProfilesEditor online={online} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiMock.get.mockReset();
  apiMock.put.mockReset();
  apiMock.get.mockImplementation(async () => STORED);
  apiMock.put.mockResolvedValue({ saved: 1 });
});
afterEach(cleanup);

describe("LinkedInProfilesEditor", () => {
  it("sunucudaki profilleri yükler, ekler, düzenler, siler ve tam listeyi kaydeder", async () => {
    renderEditor();
    expect((await screen.findByDisplayValue("Frontend")) as HTMLInputElement).toBeTruthy();

    // Ekle: boş satır.
    fireEvent.click(screen.getByRole("button", { name: /Profil ekle/ }));
    const terms = screen.getAllByPlaceholderText("Arama terimi");
    expect(terms).toHaveLength(2);
    fireEvent.change(terms[1], { target: { value: "Veri Mühendisi" } });
    fireEvent.change(screen.getAllByPlaceholderText("Konum (ops.)")[1], { target: { value: "Ankara" } });
    fireEvent.change(screen.getAllByLabelText("Sonuç sayısı")[1], { target: { value: "10" } });
    fireEvent.click(screen.getAllByLabelText("Uzak")[1]);

    // Sil: kayıtlı satır listeden çıkar.
    fireEvent.click(screen.getAllByTitle("Profili sil")[0]);
    expect(screen.queryByDisplayValue("Frontend")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Kaydet/ }));

    await waitFor(() =>
      expect(apiMock.put).toHaveBeenCalledWith("/sources/forkjob-core/linkedin-profiles", [
        { term: "Veri Mühendisi", location: "Ankara", results_wanted: 10, is_remote: true },
      ]),
    );
  });

  it("düzenlenmeyen alanları kaydederken korur", async () => {
    renderEditor();
    const term = await screen.findByDisplayValue("Frontend");
    fireEvent.change(term, { target: { value: "Frontend Developer" } });
    fireEvent.click(screen.getByRole("button", { name: /Kaydet/ }));

    await waitFor(() =>
      expect(apiMock.put).toHaveBeenCalledWith("/sources/forkjob-core/linkedin-profiles", [
        { ...STORED[0], term: "Frontend Developer" },
      ]),
    );
  });

  it("boş arama terimi varken ve çevrimdışıyken kaydetmeyi kapatır", async () => {
    renderEditor();
    await screen.findByDisplayValue("Frontend");
    expect((screen.getByRole("button", { name: /Kaydet/ }) as HTMLButtonElement).disabled).toBe(false);

    // Boş satır kaydedilemez.
    fireEvent.click(screen.getByRole("button", { name: /Profil ekle/ }));
    expect((screen.getByRole("button", { name: /Kaydet/ }) as HTMLButtonElement).disabled).toBe(true);

    cleanup();
    renderEditor(false);
    await screen.findByDisplayValue("Frontend");
    expect((screen.getByRole("button", { name: /Kaydet/ }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/Çevrimdışısın/)).toBeTruthy();
  });
});
