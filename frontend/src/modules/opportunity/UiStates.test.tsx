// @vitest-environment jsdom
/**
 * Fırsatlar UI durumları — loading/404/500/offline ayrımı.
 *
 * Kapsam:
 *  - başvuru detayı: gerçek 404 dişindaki hata (500/offline) veri yokluğu
 *    DEĞİLDİR; yeni başvuru formu çizilmez, "Tekrar dene" sunulur,
 *  - başvurular ekranı: sorgu hatası boş liste gibi gösterilmez,
 *  - sıradaki adım mevcut alanlardan türetilir (belge/gönder/takip/hazırlan),
 *  - küçük örneklemde grafikler yerine "henüz yeterli veri yok" metni çıkar,
 *  - çevrimdışıyken yazma kontrolü kapalıdır ve gerekçesi yazılıdır.
 */
import type * as ApiModule from "@/core/api";
import type { Document } from "@/core/types";
import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const harness = vi.hoisted(() => ({
  state: {
    /** `/opportunities/{id}/application` yanıtı: 200 | 404 | 500. */
    applicationStatus: 200,
    applicationsFail: false,
    applicationsTotal: 4,
  },
  post: vi.fn(async () => ({})),
  rows: [
    {
      id: "app-doc",
      title: "Belgesi Eksik Başvuru",
      organization: "Acme",
      application_status: "preparing",
      allowed_application_transitions: ["applied", "withdrawn"],
      applied_at: null,
      follow_up_at: null,
      cv_document_id: null,
    },
    {
      id: "app-send",
      title: "Gönderilmeyi Bekleyen",
      organization: "Acme",
      application_status: "preparing",
      allowed_application_transitions: ["applied", "withdrawn"],
      applied_at: null,
      follow_up_at: null,
      cv_document_id: "doc-1",
    },
    {
      id: "app-follow",
      title: "Takipli Başvuru",
      organization: "Globex",
      application_status: "applied",
      allowed_application_transitions: ["interview", "rejected"],
      applied_at: "2026-09-01T09:00:00Z",
      follow_up_at: "2026-09-15T09:00:00Z",
      cv_document_id: "doc-1",
    },
    {
      id: "app-interview",
      title: "Görüşmedeki Başvuru",
      organization: "Initech",
      application_status: "interview",
      allowed_application_transitions: ["offer", "rejected"],
      applied_at: "2026-08-20T09:00:00Z",
      follow_up_at: null,
      cv_document_id: "doc-1",
    },
  ],
}));

const LIFECYCLE = {
  job_discovery: { flow: ["discovered", "shortlisted"], transitions: {} },
  announcement: { flow: ["new", "reviewed"], transitions: {} },
  application: {
    flow: ["preparing", "applied", "interview", "offer", "accepted", "rejected", "withdrawn", "closed"],
    transitions: {
      preparing: ["applied", "withdrawn"],
      applied: ["interview", "rejected"],
      interview: ["offer", "rejected"],
      offer: ["accepted", "rejected"],
      accepted: [],
      rejected: [],
      withdrawn: ["preparing"],
      closed: [],
    },
    terminal: ["accepted", "rejected", "closed"],
  },
  trash_status: "dismissed",
  job_kinds: ["job"],
};

const APPLICATION_DETAIL = {
  opportunity_id: "opp-1",
  cv_document_id: null,
  cv_title: null,
  cv_modified_at: null,
  cover_letter: null,
  company_research: null,
  salary_expectation: null,
  posting_snapshot: {},
  note: null,
  status: "preparing",
  status_changed_at: null,
  created_at: "2026-09-01T09:00:00Z",
  updated_at: "2026-09-02T09:00:00Z",
};

vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof ApiModule>();
  const get = vi.fn(async (path: string) => {
    const { state } = harness;
    if (path.endsWith("/application")) {
      if (state.applicationStatus === 404) throw new actual.ApiError(404, "Başvuru kaydı yok");
      if (state.applicationStatus !== 200) throw new actual.ApiError(state.applicationStatus, "Sunucu hatası");
      return APPLICATION_DETAIL;
    }
    if (path.startsWith("/applications?")) {
      if (state.applicationsFail) throw new actual.ApiError(500, "Başvurular listelenemedi");
      return { items: harness.rows, total: state.applicationsTotal, offset: 0, limit: 500 };
    }
    if (path === "/applications/funnel") {
      const total = state.applicationsTotal;
      return {
        total,
        tracked: total,
        by_status: [{ status: "applied", count: total }],
        conversions: {},
        cohort: { applied: total, interview: 0, offer: 0, accepted: 0, rejected: 0 },
        cohort_size: total,
        min_cohort_size: 10,
        sufficient: false,
        rejection_reasons: [],
        avg_first_response_days: 3,
        avg_applied_to_interview_days: 7,
        by_source: [],
        by_cv: [],
        by_role: [],
        by_country: [],
        by_work_mode: [],
        weekly_volume: [],
        monthly_volume: [],
      };
    }
    if (path === "/applications/rejection-reasons") return [];
    if (path === "/opportunities/lifecycle") return LIFECYCLE;
    if (path === "/opportunities/followups") return [];
    if (path.startsWith("/opportunities/silence")) return [];
    if (path === "/documents") return [{ id: "doc-1", title: "Backend CV 2026" }];
    if (path.startsWith("/career/stories")) return [];
    return [];
  });
  return {
    api: { get, post: harness.post, patch: vi.fn(), put: vi.fn(), del: vi.fn(), upload: vi.fn() },
    ApiError: actual.ApiError,
    qs: actual.qs,
  };
});

vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));

import { ApplicationSection } from "./OpportunityDetailSections";
import { ApplicationsWorkspace } from "./ApplicationsWorkspace";

function renderInQueryClient(node: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const DOCUMENTS: Document[] = [{ id: "doc-1", title: "Backend CV 2026" } as Document];

beforeEach(() => {
  harness.state.applicationStatus = 200;
  harness.state.applicationsFail = false;
  harness.state.applicationsTotal = 4;
});

afterEach(cleanup);

describe("ApplicationSection yükleme/404/500/offline ayrımı", () => {
  it("sunucu hatasında hata gösterir ve yeni başvuru formunu ÇİZMEZ", async () => {
    harness.state.applicationStatus = 500;
    renderInQueryClient(<ApplicationSection id="opp-1" online documents={DOCUMENTS} />);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Başvuru bilgisi yüklenemedi");
    expect(screen.getByRole("button", { name: "Tekrar dene" })).toBeTruthy();
    // Sunucu hatası "başvuru yok" değildir: form ve Başvur düğmesi çizilmez.
    expect(screen.queryByRole("button", { name: "Başvur" })).toBeNull();
    expect(screen.queryByText("CV seç (varsa)")).toBeNull();
  });

  it("gerçek 404'te form açılır (hata değil, kayıt yok)", async () => {
    harness.state.applicationStatus = 404;
    renderInQueryClient(<ApplicationSection id="opp-1" online documents={DOCUMENTS} />);

    expect(await screen.findByRole("button", { name: "Başvur" })).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("çevrimdışıyken okunamayan başvuruda çevrimdışı gerekçesini yazar", async () => {
    harness.state.applicationStatus = 503;
    renderInQueryClient(<ApplicationSection id="opp-1" online={false} documents={DOCUMENTS} />);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Çevrimdışısın");
    expect(screen.queryByRole("button", { name: "Başvur" })).toBeNull();
  });
});

describe("ApplicationsWorkspace hata ve offline durumları", () => {
  it("başvuru listesi hata verdiğinde hata metnini gösterir, boş liste demez", async () => {
    harness.state.applicationsFail = true;
    renderInQueryClient(<ApplicationsWorkspace online onOpen={vi.fn()} />);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Başvurular yüklenemedi");
    expect(screen.getByRole("button", { name: "Tekrar dene" })).toBeTruthy();
    expect(screen.queryByText("Henüz gerçek başvuru yok")).toBeNull();
  });

  it("çevrimdışıyken başvuru ilerletme kontrolü kapalı ve gerekçesi yazılıdır", async () => {
    renderInQueryClient(<ApplicationsWorkspace online={false} onOpen={vi.fn()} />);

    const select = (await screen.findByLabelText("Takipli Başvuru başvuru durumunu değiştir")) as HTMLSelectElement;
    expect(select.disabled).toBe(true);
    expect(screen.getByText(/Çevrimdışısın: başvuru durumu değiştirilemez/)).toBeTruthy();

    // Çevrimiçi aynı kontrol açıktır: test yanlış sebeple geçmiyor.
    cleanup();
    renderInQueryClient(<ApplicationsWorkspace online onOpen={vi.fn()} />);
    const onlineSelect = (await screen.findByLabelText(
      "Takipli Başvuru başvuru durumunu değiştir",
    )) as HTMLSelectElement;
    expect(onlineSelect.disabled).toBe(false);
  });

  it("liste satırlarında sıradaki adımı mevcut alanlardan türetir", async () => {
    renderInQueryClient(<ApplicationsWorkspace online onOpen={vi.fn()} />);
    await screen.findByText("Belgesi Eksik Başvuru");

    expect(screen.getByText("Belge tamamla")).toBeTruthy();
    expect(screen.getByText("Başvuru gönder")).toBeTruthy();
    expect(screen.getByText("Takip et")).toBeTruthy();
    expect(screen.getByText("Görüşmeye hazırlan")).toBeTruthy();
  });

  it("küçük örneklemde grafikler yerine 'henüz yeterli veri yok' metni koyar", async () => {
    harness.state.applicationsTotal = 1;
    renderInQueryClient(<ApplicationsWorkspace online onOpen={vi.fn()} />);
    await screen.findByText("Belgesi Eksik Başvuru");
    expect(screen.queryByText("Kohort dönüşümü")).toBeNull();
    fireEvent.click(screen.getByRole("tab", { name: "İstatistik" }));

    expect(screen.getByText("Henüz yeterli veri yok")).toBeTruthy();
    expect(screen.queryByText("Kohort dönüşümü")).toBeNull();
    expect(screen.queryByText("Durum dağılımı")).toBeNull();
    expect(screen.queryByText("Kaynağa göre")).toBeNull();

    // Haftalık/aylık ritim grafikleri istatistikte de küçük örneklemde gizlenir.
    expect(await screen.findByText(/başvuru ritmi grafikleri en az 3 gerçek başvuru/)).toBeTruthy();
    expect(screen.queryByText("Haftalık başvuru ritmi")).toBeNull();
    expect(screen.queryByText("Aylık başvuru ritmi")).toBeNull();
  });
});
