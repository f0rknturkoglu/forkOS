// @vitest-environment jsdom
/**
 * AnnouncementDetail — duyuru çalışma yüzeyi (Faz 4.3).
 *
 * Kapsam:
 *  - duyuru yüzeyi iş ilanı alanlarını (maaş, çalışma biçimi, warm intro,
 *    şirket notları, görüşmeler) HİÇBİR sekmede render etmez,
 *  - bilinmeyen değerler uydurulmaz, `—` gösterilir,
 *  - kontenjan/alan/tarih/aşama alanları backend sözleşmesinden okunur,
 *  - ana kılavuz bağlantısı `?focus=<parent_id>` adresini açar,
 *  - durum aksiyonları yalnızca `allowed_transitions` ile sınırlıdır.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type * as ObsidianModule from "@/core/obsidian";
import type { Opportunity } from "@/core/types";

const obsidianHarness = vi.hoisted(() => ({ openUri: vi.fn() }));
const invalidationHarness = vi.hoisted(() => ({ invalidate: vi.fn() }));

vi.mock("@/core/obsidian", async (orig) => {
  const actual = await orig<typeof ObsidianModule>();
  return { ...actual, openObsidianUri: (uri: string) => obsidianHarness.openUri(uri) };
});
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => invalidationHarness.invalidate(...events),
}));
vi.mock("@/core/queryClient", () => ({ queryClient: vi.fn() }));

vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(() => ({ data: [], isLoading: false, isFetching: false, refetch: vi.fn() })),
  useMutation: vi.fn((options: { mutationFn: (vars: unknown) => unknown; onSuccess?: (value: unknown) => void }) => ({
    isPending: false,
    mutate: (vars: unknown) => {
      const result = options.mutationFn(vars);
      if (result && typeof (result as Promise<unknown>).then === "function") {
        void (result as Promise<unknown>).then((value) => options.onSuccess?.(value));
      }
    },
  })),
}));

vi.mock("@/core/api", () => ({
  api: {
    get: vi.fn(() => Promise.resolve([])),
    post: vi.fn(() => Promise.resolve({})),
    patch: vi.fn(() => Promise.resolve({})),
    put: vi.fn(() => Promise.resolve({})),
    del: vi.fn(() => Promise.resolve()),
  },
  qs: (params: Record<string, string | number | boolean | undefined | null>) => {
    const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
    return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
  },
}));

vi.mock("@/core/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/ui")>();
  return { ...actual, useToast: () => ({ push: vi.fn() }) };
});
vi.mock("@/lib/hooks", () => ({ useOnline: () => true, useDebounced: (value: string) => value }));
vi.mock("@/core/SaveToLibrary", () => ({ useSaveToLibrary: () => ({ save: vi.fn() }) }));
vi.mock("@/app/router", () => ({ navigate: vi.fn() }));

import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { AnnouncementDetail } from "./AnnouncementDetail";

const ANNOUNCEMENT: Opportunity = {
  id: "ann-1",
  title: "2026 YLSY Başvuru Kılavuzu",
  kind: "scholarship",
  category: "ylsy-application",
  organization: "YÖK",
  url: "https://yok.example/duyuru/1",
  status: "new",
  allowed_transitions: ["reviewed", "watching", "action_required", "expired", "archived"],
  priority: 2,
  found_at: "2026-08-01T10:00:00Z",
  published_at: "2026-07-30T10:00:00Z",
  deadline_at: null,
  applied_at: null,
  location: null,
  remote: null,
  compensation: null,
  source: "ylsy",
  external_id: null,
  raw: {},
  score: null,
  score_source: null,
  score_computed_at: null,
  score_reasons: null,
  notes: null,
  trashed_at: null,
  trashed_from_status: null,
  country: "TR",
  region: "TR",
  follow_up_at: null,
  rejection_reason: null,
  profile_match_ratio: null,
  skill_match: null,
  application_status: null,
  application_status_changed_at: null,
  allowed_application_transitions: [],
  intelligence: null,
  evaluation: null,
  source_status: "active",
  last_seen_at: "2026-09-05T10:00:00Z",
  closed_at: null,
  official: true,
  parent_id: "guide-1",
  stage: "başvuru",
  application_start_at: "2026-08-10T00:00:00Z",
  application_end_at: "2026-09-10T00:00:00Z",
  exam_at: "2026-10-05T00:00:00Z",
  result_at: "2026-11-20T00:00:00Z",
  guide_url: "https://yok.example/kilavuz.pdf",
  apply_url: "https://ais.osym.gov.tr/basvuru",
  quota_total: 120,
  fields: ["Mühendislik", "Sağlık Bilimleri"],
};

/** İş ilanına özel metinler duyuruda hiçbir sekmede görünmemeli. */
const JOB_ONLY_STRINGS = [
  "Maaş",
  "Ücret",
  "Ofis",
  "Uzaktan",
  "Hibrit",
  "Çalışma biçimi",
  "Warm intro",
  "Şirket Notları",
  "Görüşme",
  "CV Değerlendirmesi",
];

const TAB_NAMES = ["Özet", "Tarihler ve Aşamalar", "Kontenjan ve Koşullar", "Belgeler", "Notlar ve İlişkiler"];

afterEach(cleanup);

describe("AnnouncementDetail", () => {
  it("tüm sekmelerde iş ilanı yüzeylerini render etmez", () => {
    render(<AnnouncementDetail item={ANNOUNCEMENT} />);
    for (const tab of TAB_NAMES) {
      fireEvent.click(screen.getByRole("tab", { name: tab }));
      const text = document.body.textContent ?? "";
      for (const forbidden of JOB_ONLY_STRINGS) {
        expect(text.includes(forbidden)).toBe(false);
      }
    }
  });

  it("duyuru künyesini kurum, resmîlik ve kaynakla gösterir", () => {
    render(<AnnouncementDetail item={ANNOUNCEMENT} />);
    expect(screen.getByText("Duyuru künyesi")).toBeTruthy();
    expect(screen.getByText("YÖK")).toBeTruthy();
    expect(screen.getAllByText("Resmî kaynak").length).toBeGreaterThan(0);
    expect(screen.getAllByText("YLSY başvuru").length).toBeGreaterThan(0);
    expect(screen.getByText("Başvuru adresi")).toBeTruthy();
    expect(screen.getByText("Kılavuz")).toBeTruthy();
  });

  it("kontenjan ve koşullar sekmesi kontenjanı ve alanları gösterir", () => {
    render(<AnnouncementDetail item={ANNOUNCEMENT} />);
    fireEvent.click(screen.getByRole("tab", { name: "Kontenjan ve Koşullar" }));
    expect(screen.getByText("120")).toBeTruthy();
    expect(screen.getByText("kişilik kontenjan")).toBeTruthy();
    expect(screen.getByText("Mühendislik")).toBeTruthy();
    expect(screen.getByText("Sağlık Bilimleri")).toBeTruthy();
  });

  it("tarihler sekmesi başvuru penceresini, sınavı ve sonucu gösterir", () => {
    render(<AnnouncementDetail item={ANNOUNCEMENT} />);
    fireEvent.click(screen.getByRole("tab", { name: "Tarihler ve Aşamalar" }));
    expect(screen.getByText("Başvuru başlangıcı")).toBeTruthy();
    expect(screen.getByText("Başvuru bitişi")).toBeTruthy();
    expect(screen.getByText("Sınav")).toBeTruthy();
    expect(screen.getByText("Sonuç")).toBeTruthy();
    expect(screen.getAllByText("başvuru").length).toBeGreaterThan(0);
  });

  it("bilinmeyen değerleri uydurmaz, — gösterir", () => {
    render(<AnnouncementDetail item={{ ...ANNOUNCEMENT, official: null, quota_total: null, fields: [] }} />);
    expect(screen.getAllByText("Kaynak türü —").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("tab", { name: "Kontenjan ve Koşullar" }));
    expect(screen.getByText("Kontenjan bilgisi bu duyuruda yer almıyor.")).toBeTruthy();
    expect(screen.getByText("Alan / koşul bilgisi bu duyuruda yer almıyor.")).toBeTruthy();
  });

  it("ana kılavuz bağlantısı focus parametresiyle açar", () => {
    render(<AnnouncementDetail item={ANNOUNCEMENT} />);
    fireEvent.click(screen.getByRole("button", { name: "Ana kılavuza git" }));
    expect(vi.mocked(navigate)).toHaveBeenCalledWith("/opportunities?focus=guide-1");
  });

  it("durum aksiyonları yalnızca izinli keşif geçişleridir", () => {
    render(<AnnouncementDetail item={{ ...ANNOUNCEMENT, allowed_transitions: ["watching", "archived"] }} />);
    expect(screen.queryByRole("button", { name: "Okundu işaretle" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Takibe al" }));
    expect(vi.mocked(api.post)).toHaveBeenCalledWith("/opportunities/ann-1/transition", { to: "watching" });
    fireEvent.click(screen.getByRole("button", { name: "Arşivle" }));
    expect(vi.mocked(api.post)).toHaveBeenCalledWith("/opportunities/ann-1/transition", { to: "archived" });
  });

  it("duyuru notu Vault'ta yakalanır ve Obsidian'da açılır; /notes'a yazılmaz", async () => {
    vi.mocked(api.post).mockResolvedValue({
      forkos_id: "vault-ann-1",
      open_uri: "obsidian://open?vault=f0rknbrain&file=00%20Inbox%2FYLSY",
    });
    render(<AnnouncementDetail item={ANNOUNCEMENT} />);
    fireEvent.click(screen.getByRole("tab", { name: "Notlar ve İlişkiler" }));

    // Serbest yakalama: kanonik dosya YOK, hep olusturma aksiyonu sunulur.
    expect(screen.queryByRole("button", { name: "Obsidian'da aç" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Duyuru notu oluştur" }));

    await waitFor(() => expect(obsidianHarness.openUri).toHaveBeenCalled());
    expect(obsidianHarness.openUri).toHaveBeenCalledWith("obsidian://open?vault=f0rknbrain&file=00%20Inbox%2FYLSY");
    const [path, body] = vi.mocked(api.post).mock.calls.find(([call]) => String(call).includes("obsidian")) ?? [];
    expect(path).toBe("/obsidian/capture");
    expect(body).toEqual({
      body: expect.stringContaining("2026 YLSY Başvuru Kılavuzu"),
      relate_to: "ann-1",
      tags: ["duyuru"],
    });
    expect(vi.mocked(api.post).mock.calls.some(([call]) => String(call) === "/notes")).toBe(false);
    expect(invalidationHarness.invalidate).toHaveBeenCalledWith("obsidian.write");
    expect(invalidationHarness.invalidate).not.toHaveBeenCalledWith("note.write", "opportunity.write");
  });
});
