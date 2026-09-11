// @vitest-environment jsdom
/**
 * Başvurular çalışma alanı (Faz 4.1) — payda yalnızca gerçek başvurular.
 *
 * Kapsam:
 *  - keşfedilen ilanlar çalışma alanına girmez (`/opportunities/browse` hiç çağrılmaz),
 *  - kanban kovaları `application.status`'tan türetilir (lifecycle),
 *  - null oran "—" olur, yanıltıcı "%0" yazılmaz,
 *  - geçiş seçenekleri yalnızca `allowed_application_transitions`'tır.
 */
import type * as UiModule from "@/core/ui";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const harness = vi.hoisted(() => {
  const lifecycle = {
    job_discovery: {
      flow: ["discovered", "shortlisted", "dismissed", "archived", "closed"],
      transitions: {},
    },
    announcement: { flow: ["new", "reviewed", "archived"], transitions: {} },
    application: {
      flow: ["preparing", "applied", "interview", "offer", "accepted", "rejected", "withdrawn", "closed"],
      transitions: {
        preparing: ["applied", "withdrawn", "closed"],
        applied: ["preparing", "interview", "offer", "rejected", "withdrawn", "closed"],
        interview: ["applied", "offer", "rejected", "withdrawn", "closed"],
        offer: ["accepted", "rejected", "withdrawn", "closed"],
        accepted: [],
        rejected: [],
        withdrawn: ["preparing"],
        closed: [],
      },
      terminal: ["accepted", "rejected", "closed"],
    },
    trash_status: "dismissed",
    job_kinds: ["job", "internship"],
  };

  const applications = [
    {
      id: "app-1",
      title: "Backend Engineer",
      organization: "Acme",
      status: "shortlisted",
      application_status: "applied",
      application_status_changed_at: "2026-09-08T09:00:00Z",
      allowed_application_transitions: ["preparing", "interview", "offer", "rejected", "withdrawn", "closed"],
      applied_at: "2026-09-01T09:00:00Z",
      follow_up_at: "2026-09-15T09:00:00Z",
      cv_document_id: "doc-1",
    },
    {
      id: "app-2",
      title: "Data Scientist",
      organization: "Globex",
      status: "shortlisted",
      application_status: "offer",
      application_status_changed_at: "2026-09-09T09:00:00Z",
      allowed_application_transitions: ["accepted", "rejected", "withdrawn", "closed"],
      applied_at: "2026-08-20T09:00:00Z",
      follow_up_at: null,
      cv_document_id: null,
    },
    {
      id: "app-3",
      title: "DevOps Engineer",
      organization: "Initech",
      status: "archived",
      application_status: "withdrawn",
      application_status_changed_at: "2026-09-05T09:00:00Z",
      allowed_application_transitions: ["preparing"],
      applied_at: "2026-08-01T09:00:00Z",
      follow_up_at: null,
      cv_document_id: null,
    },
  ];

  const byStatus = ["preparing", "applied", "interview", "offer", "accepted", "rejected", "withdrawn", "closed"].map(
    (status) => ({ status, count: { applied: 1, offer: 1, withdrawn: 1 }[status] ?? 0 }),
  );

  const funnel = {
    total: 3,
    tracked: 3,
    by_status: byStatus,
    conversions: { applied_to_interview: null },
    rejection_reasons: [{ reason: "uyum yetersiz", count: 0 }],
    avg_first_response_days: null,
    avg_applied_to_interview_days: 7,
    by_source: [
      {
        key: "jobhunter:linkedin",
        label: "jobhunter:linkedin",
        total: 3,
        responded: 1,
        interviewed: 0,
        offers: 0,
        response_rate: null,
        interview_rate: null,
      },
    ],
    by_cv: [],
    by_role: [],
    by_country: [],
    by_work_mode: [],
    weekly_volume: [{ period: "2026-W36", applied: 2 }],
    monthly_volume: [{ period: "2026-09", applied: 2 }],
  };

  const followups = [
    {
      id: "app-1",
      title: "Backend Engineer",
      status: "applied",
      follow_up_at: "2026-09-15T09:00:00Z",
      note: null,
    },
  ];
  const silence = [
    {
      id: "app-2",
      title: "Data Scientist",
      organization: "Globex",
      status: "interview",
      last_interview_at: "2026-08-01T09:00:00Z",
      days_silent: 40,
    },
  ];
  const documents = [{ id: "doc-1", title: "Backend CV 2026" }];

  const get = vi.fn(async (path: string) => {
    if (path.startsWith("/applications?")) return applications;
    if (path === "/applications/funnel") return funnel;
    if (path === "/applications/rejection-reasons") return ["maas uyumsuz", "uyum yetersiz"];
    if (path === "/opportunities/lifecycle") return lifecycle;
    if (path === "/opportunities/followups") return followups;
    if (path.startsWith("/opportunities/silence")) return silence;
    if (path === "/documents") return documents;
    // Keşif verisi: çalışma alanı bunu ASLA okumamalı.
    if (path.startsWith("/opportunities/browse"))
      return { items: [{ id: "discovered-1", title: "Keşfedilmiş İlan" }], total: 1 };
    return [];
  });
  const post = vi.fn(async () => ({}));

  return { lifecycle, applications, funnel, followups, silence, documents, get, post };
});

vi.mock("@/core/api", () => ({
  api: { get: harness.get, post: harness.post, patch: vi.fn(), del: vi.fn() },
  qs: (params: Record<string, unknown>) => {
    const entries = Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== "");
    return entries.length ? `?${new URLSearchParams(entries.map(([key, value]) => [key, String(value)]))}` : "";
  },
}));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/core/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof UiModule>();
  return { ...actual, useToast: () => ({ push: vi.fn() }) };
});

import { ApplicationsWorkspace } from "./ApplicationsWorkspace";

function renderWorkspace(onOpen: (id: string) => void = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <QueryClientProvider client={client}>
      <ApplicationsWorkspace online onOpen={onOpen} />
    </QueryClientProvider>,
  );
  return { ...view, onOpen };
}

afterEach(() => {
  cleanup();
  harness.get.mockClear();
  harness.post.mockClear();
});

describe("ApplicationsWorkspace", () => {
  it("yalnızca gerçek başvuruları okur ve paydayı açıkça yazar", async () => {
    const view = renderWorkspace();
    await screen.findAllByText("Backend Engineer");

    expect(harness.get).toHaveBeenCalledWith("/applications?limit=500");
    expect(harness.get).not.toHaveBeenCalledWith(expect.stringContaining("/opportunities/browse"));
    expect(screen.getAllByText("Payda: yalnızca gerçek başvurular").length).toBeGreaterThan(0);
    expect(view.queryByText("Keşfedilmiş İlan")).toBeNull();
    // Backend CV adı belge kaydından çözülür.
    expect(screen.getByText("Backend CV 2026")).toBeTruthy();
  });

  it("kanban kovalarını application durumlarından türetir", async () => {
    renderWorkspace();
    await screen.findAllByText("Backend Engineer");
    fireEvent.click(screen.getByRole("tab", { name: "Kanban" }));

    const columns = ["Hazırlanıyor", "Başvuruldu", "Görüşme", "Teklif", "Sonuçlandı"];
    for (const title of columns) {
      expect(await screen.findByRole("region", { name: title })).toBeTruthy();
    }

    const applied = screen.getByRole("region", { name: "Başvuruldu" });
    expect(within(applied).getByText("1")).toBeTruthy();
    expect(within(applied).getByText("Backend Engineer")).toBeTruthy();
    const offer = screen.getByRole("region", { name: "Teklif" });
    expect(within(offer).getByText("1")).toBeTruthy();
    expect(within(offer).getByText("Data Scientist")).toBeTruthy();
    // withdrawn lifecycle'ın terminal listesinde değil ama kapanmış kovada.
    const concluded = screen.getByRole("region", { name: "Sonuçlandı" });
    expect(within(concluded).getByText("1")).toBeTruthy();
    expect(within(concluded).getByText("DevOps Engineer")).toBeTruthy();
    // Boş kova sayacı 0 yazar.
    expect(within(screen.getByRole("region", { name: "Görüşme" })).getByText("0")).toBeTruthy();
  });

  it("null oranı '—' gösterir, yanıltıcı '%0' yazmaz", async () => {
    renderWorkspace();
    await screen.findByText("linkedin");

    const row = screen.getByText("linkedin").parentElement;
    expect(row?.textContent).toContain("—");
    expect(screen.queryAllByText("0%")).toHaveLength(0);
    // Ortalama ilk yanıt süresi de null: metrik "—" olmalı.
    expect(screen.getByText("Ort. ilk yanıt").parentElement?.textContent).toContain("—");
  });

  it("sessiz başvuruyu listeler ve kayda bağlar", async () => {
    const { onOpen } = renderWorkspace();
    const heading = await screen.findByText("Firma sessizliği");
    const section = heading.closest("section");
    expect(section).toBeTruthy();
    const record = await within(section!).findByText("Data Scientist");
    expect(within(section!).getByText("40 gün")).toBeTruthy();

    fireEvent.click(record);
    expect(onOpen).toHaveBeenCalledWith("app-2");
  });

  it("durum geçişini yalnızca allowed_application_transitions ile sunar", async () => {
    renderWorkspace();
    await screen.findAllByText("Backend Engineer");

    const select = (await screen.findByLabelText("Backend Engineer başvuru durumunu değiştir")) as HTMLSelectElement;
    const options = within(select)
      .getAllByRole("option")
      .map((option) => (option as HTMLOptionElement).value);

    expect(options).toContain("interview");
    expect(options).not.toContain("accepted");

    fireEvent.change(select, { target: { value: "interview" } });
    await waitFor(() =>
      expect(harness.post).toHaveBeenCalledWith("/applications/app-1/transition", { to: "interview" }),
    );
  });
});
