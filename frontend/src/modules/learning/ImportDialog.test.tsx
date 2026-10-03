// @vitest-environment jsdom
/**
 * Ice aktarma diyalogu (Faz 9): onizleme olmadan uygulanmaz, girdi degisince
 * onizleme bayatlar, prune ayri ve varsayilan kapali onaydir.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { components } from "@/generated/api-schema";
import { ImportDialog } from "./ImportDialog";

type ImportPreview = components["schemas"]["ImportPreviewOut"];
type ImportResult = components["schemas"]["TopicImportOut"];

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  onClose: vi.fn(),
  onDone: vi.fn(),
  toast: vi.fn(),
}));

vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return { ...actual, api: { ...actual.api, get: harness.apiGet, post: harness.apiPost } };
});
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));

vi.mock("@/core/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/ui")>();
  return { ...actual, useToast: () => ({ push: harness.toast }) };
});

const AREA_TITLE = "Makine Öğrenmesi";
const TREE = JSON.stringify({
  area: AREA_TITLE,
  topics: [{ title: "Doğrusal Modeller", status: "in_progress" }],
});

const PREVIEW: ImportPreview = {
  area: { id: null, title: AREA_TITLE, exists: false },
  creates: [
    {
      path: `${AREA_TITLE}/Doğrusal Modeller`,
      title: "Doğrusal Modeller",
      status: "not_started",
      resources: 2,
      changes: [],
    },
  ],
  updates: [],
  matches: [],
  resources_new: 3,
  resources_duplicate: 1,
  conflicts: [{ path: `${AREA_TITLE}/Doğrusal Modeller`, reason: "başlık boş" }],
  invalid: [],
  suggested_prefix: "ilk90_ales - ",
  totals: { nodes: 1, depth: 1, creates: 1, updates: 0, matches: 0 },
};

const RESULT: ImportResult = {
  area_id: "area-9",
  area_title: AREA_TITLE,
  topics_created: 1,
  topics_matched: 0,
  topics_updated: 0,
  resources_created: 3,
  resources_skipped: 1,
  resources_updated: 0,
  topics_archived: 0,
  resources_archived: 0,
};

function renderDialog() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ImportDialog open onClose={harness.onClose} onDone={harness.onDone} />
    </QueryClientProvider>,
  );
}

const applyButton = () => screen.getByRole("button", { name: "Uygula" }) as HTMLButtonElement;

beforeEach(() => {
  harness.apiGet.mockReset().mockResolvedValue([]);
  harness.apiPost.mockReset().mockImplementation(async (path: string) => {
    if (path === "/study/import/preview") return PREVIEW;
    return RESULT;
  });
  harness.invalidate.mockReset();
  harness.onClose.mockReset();
  harness.onDone.mockReset();
  harness.toast.mockReset();
});
afterEach(cleanup);

describe("ImportDialog", () => {
  it("dosya seçildiğinde açık bildirim verir ve henüz yazmaz", async () => {
    renderDialog();
    const file = document.querySelector('input[type="file"]')!;
    fireEvent.change(file, { target: { files: [{ name: "python.json", text: async () => TREE }] } });
    await screen.findByText(/python.json okundu/);
    expect(harness.toast).toHaveBeenCalledWith(expect.stringContaining("Henüz eklenmedi"), { tone: "ok" });
    expect(harness.apiPost).not.toHaveBeenCalled();
    expect(applyButton().disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: /Önizle/ }));
    await screen.findByText("Yeni alan");
    expect(harness.toast).toHaveBeenCalledWith(expect.stringContaining("Önizleme hazır"), { tone: "ok" });
  });

  it("bozuk dosyayı bildirir ve önceki önizlemeyi temizler", async () => {
    renderDialog();
    fireEvent.change(screen.getByLabelText("İçe aktarılacak JSON"), { target: { value: TREE } });
    fireEvent.click(screen.getByRole("button", { name: /Önizle/ }));
    await screen.findByText("Yeni alan");
    fireEvent.change(document.querySelector('input[type="file"]')!, {
      target: { files: [{ name: "broken.json", text: async () => "{bad" }] },
    });
    await screen.findByRole("alert");
    expect(applyButton().disabled).toBe(true);
    expect(harness.toast).toHaveBeenCalledWith(expect.stringContaining("Dosya okunamadı"), { tone: "danger" });
  });

  it("sunucu hatasını hem modalda hem bildirimde gösterir", async () => {
    harness.apiPost.mockRejectedValue(new Error("Konu sınırı aşıldı"));
    renderDialog();
    fireEvent.change(screen.getByLabelText("İçe aktarılacak JSON"), { target: { value: TREE } });
    fireEvent.click(screen.getByRole("button", { name: /Önizle/ }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(harness.toast).toHaveBeenCalledWith(expect.stringContaining("Konu sınırı aşıldı"), { tone: "danger" });
  });
  it("onizleme gorulmeden uygulanmaz; onizleme diff'i cizer", async () => {
    renderDialog();
    const json = screen.getByLabelText("İçe aktarılacak JSON");

    fireEvent.change(json, { target: { value: TREE } });
    expect(applyButton().disabled).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: /Önizle/ }));
    await screen.findByText("Yeni alan");

    expect(harness.apiPost).toHaveBeenCalledWith("/study/import/preview", {
      topics: [{ title: "Doğrusal Modeller", status: "in_progress" }],
      update_existing: true,
      strip_common_prefix: false,
      prune: false,
      area: AREA_TITLE,
    });
    expect(screen.getByText("Eklenecek konular (1)")).toBeTruthy();
    expect(screen.getByText("Yeni kaynak")).toBeTruthy();
    expect(screen.getByText("Çakışmalar (1)")).toBeTruthy();
    expect(screen.getByText(/başlık boş/)).toBeTruthy();
    expect(applyButton().disabled).toBe(false);
  });

  it("uygular, sonucu ozetler ve onDone(areaId) cagirir", async () => {
    renderDialog();
    fireEvent.change(screen.getByLabelText("İçe aktarılacak JSON"), { target: { value: TREE } });
    fireEvent.click(screen.getByRole("button", { name: /Önizle/ }));
    await screen.findByText("Yeni alan");

    fireEvent.click(applyButton());
    await waitFor(() =>
      expect(harness.apiPost).toHaveBeenCalledWith("/study/import", {
        topics: [{ title: "Doğrusal Modeller", status: "in_progress" }],
        update_existing: true,
        strip_common_prefix: false,
        prune: false,
        area: AREA_TITLE,
      }),
    );

    expect(await screen.findByText(/güncellendi/)).toBeTruthy();
    expect(harness.invalidate).toHaveBeenCalledWith("study.write");

    fireEvent.click(screen.getByRole("button", { name: "Tamam" }));
    expect(harness.onDone).toHaveBeenCalledWith("area-9");
  });

  it("girdi degisince onizleme bayatlar ve Uygula kapanir", async () => {
    renderDialog();
    const json = screen.getByLabelText("İçe aktarılacak JSON");
    fireEvent.change(json, { target: { value: TREE } });
    fireEvent.click(screen.getByRole("button", { name: /Önizle/ }));
    await screen.findByText("Yeni alan");
    expect(applyButton().disabled).toBe(false);

    fireEvent.change(json, { target: { value: `${TREE} ` } });
    expect(await screen.findByText(/önizleme geçersiz/)).toBeTruthy();
    expect(applyButton().disabled).toBe(true);
  });

  it("prune varsayilan kapali; onizleme yenilenmeden uygulanamaz", async () => {
    renderDialog();
    fireEvent.change(screen.getByLabelText("İçe aktarılacak JSON"), { target: { value: TREE } });
    fireEvent.click(screen.getByRole("button", { name: /Önizle/ }));
    await screen.findByText("Yeni alan");

    const prune = screen.getByLabelText(/arşivle \(prune\)/) as HTMLInputElement;
    expect(prune.checked).toBe(false);
    fireEvent.click(prune);
    expect(applyButton().disabled).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: /Önizle/ }));
    await waitFor(() => expect(applyButton().disabled).toBe(false));
    fireEvent.click(applyButton());
    await waitFor(() =>
      expect(harness.apiPost).toHaveBeenCalledWith("/study/import", expect.objectContaining({ prune: true })),
    );
  });

  it("bozuk JSON'da istek atmaz, hatayi duyurur", async () => {
    renderDialog();
    fireEvent.change(screen.getByLabelText("İçe aktarılacak JSON"), { target: { value: "{bozuk" } });
    fireEvent.click(screen.getByRole("button", { name: /Önizle/ }));

    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByText(/JSON okunamadı/)).toBeTruthy();
    expect(harness.apiPost).not.toHaveBeenCalled();
  });

  it("onizlemede onek onerisi varsa onay kutusu cikar", async () => {
    renderDialog();
    fireEvent.change(screen.getByLabelText("İçe aktarılacak JSON"), { target: { value: TREE } });
    fireEvent.click(screen.getByRole("button", { name: /Önizle/ }));
    await screen.findByText("Yeni alan");

    fireEvent.click(screen.getByLabelText(/Ortak başlık önekini temizle/));
    fireEvent.click(screen.getByRole("button", { name: /Önizle/ }));
    await waitFor(() =>
      expect(harness.apiPost).toHaveBeenCalledWith(
        "/study/import/preview",
        expect.objectContaining({ strip_common_prefix: true }),
      ),
    );
  });
});
