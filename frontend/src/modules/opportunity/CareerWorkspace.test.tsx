// @vitest-environment jsdom
/**
 * CareerWorkspace — beş kariyer çalışma alanı sekmesinin sözleşmeleri.
 *
 * Kapsam: hikâye düzenleyicisi tıklanana kadar kapalı, CSV içe aktarma
 * önizlemesi + tekrar sayısı + yerel-only beyanı, duyuru kayıtlarının
 * "Şirket Notu" taşımaması, Jobhunter Basit/Advanced ayrımı ve derin bağ.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type * as UiModule from "@/core/ui";
import type {
  Application,
  CareerConnection,
  CareerStory,
  Interview,
  Opportunity,
  SalaryConsistency,
} from "@/core/types";

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
  upload: vi.fn(),
}));

vi.mock("@/core/api", () => ({ api: apiMock, qs: () => "" }));
vi.mock("@/core/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof UiModule>();
  return { ...actual, useToast: () => ({ push: vi.fn() }) };
});
vi.mock("@/core/dialog", () => ({ confirmDialog: vi.fn(async () => false) }));

import { CareerWorkspace } from "./CareerWorkspace";

const STORY: CareerStory = {
  id: "s1",
  title: "Ölçekleme hikâyesi",
  situation: "Yoğun trafik",
  task: "Dayanıklılık",
  action: "Önbellek katmanı",
  result: "Gecikme %40 düştü",
  reflection: "Ölçüm şart",
  provenance: "existing",
  tags: ["ölçekleme"],
  updated_at: "2026-01-01T00:00:00Z",
};

const CONNECTIONS: CareerConnection[] = [
  {
    id: "c1",
    name: "Ada Lovelace",
    first_name: "Ada",
    last_name: "Lovelace",
    profile_url: "https://linkedin.com/in/ada",
    email: null,
    company: "Acme Inc.",
    position: "CTO",
    connected_on: "2026-01-02",
  },
];

function opportunity(over: Record<string, unknown>): Opportunity {
  return {
    id: "a1",
    title: "Backend Engineer",
    kind: "job",
    category: "software",
    organization: "Acme Inc.",
    url: null,
    status: "shortlisted",
    allowed_transitions: [],
    priority: 0,
    found_at: "2026-01-01T00:00:00Z",
    published_at: null,
    deadline_at: null,
    applied_at: "2026-01-05T00:00:00Z",
    location: null,
    remote: null,
    compensation: null,
    source: "test",
    external_id: null,
    raw: {},
    score: 80,
    score_reasons: null,
    notes: null,
    trashed_at: null,
    trashed_from_status: null,
    country: null,
    region: null,
    follow_up_at: null,
    rejection_reason: null,
    application_status: "interview",
    allowed_application_transitions: [],
    ...over,
  } as unknown as Opportunity;
}

const APPLICATION = opportunity({
  evaluation: {
    version: "career-ops-v1",
    evaluated_at: "2026-01-06T00:00:00Z",
    source_fingerprint: "fp",
    engine: "local_rules",
    candidate_source: "profile",
    candidate_document_id: null,
    candidate_document_title: null,
    archetype: null,
    archetype_scores: {},
    score: 80,
    recommendation: "pursue",
    requirements: [],
    matches: [
      {
        requirement_id: "r1",
        requirement: "Go",
        match: "strong",
        evidence: "Üretimde Go",
        gap_mitigation: null,
        story_ids: [STORY.id],
      },
    ],
    gate: {
      job_country: null,
      authorized_to_work: true,
      sponsorship_status: "unstated",
      geo_mismatch: false,
      hard_blocker: false,
      reasons: [],
    },
    notes: null,
  },
});

const ANNOUNCEMENT = opportunity({
  id: "n1",
  title: "YLSY kılavuzu",
  kind: "exam",
  category: "ylsy-guide",
  status: "new",
  application_status: null,
  applied_at: null,
  evaluation: null,
  source: "osym",
});

const APPLICATION_DETAIL: Application = {
  opportunity_id: "a1",
  cv_document_id: null,
  cv_title: null,
  cv_modified_at: null,
  cover_letter: "Ölçekleme deneyimimle gecikmeyi düşürdüm.",
  company_research: "",
  salary_expectation: null,
  posting_snapshot: {},
  note: null,
  status: "interview",
  status_changed_at: null,
  created_at: "2026-01-05T00:00:00Z",
  updated_at: "2026-01-06T00:00:00Z",
};

const CSV = [
  "Notes:",
  '"LinkedIn veri disa aktarimi"',
  "",
  "First Name,Last Name,URL,Email Address,Company,Position,Connected On",
  "Ada,Lovelace,https://linkedin.com/in/ada,,Acme Inc.,CTO,02 Jan 2026",
  "Grace,Hopper,,grace@example.com,Acme Inc.,Advisor,03 Jan 2026",
].join("\n");

function mockGet(path: string): unknown {
  if (path.startsWith("/opportunities/lifecycle")) {
    return {
      job_discovery: { flow: ["discovered", "shortlisted"], transitions: {} },
      announcement: { flow: ["new", "reviewed"], transitions: {} },
      application: { flow: ["preparing", "applied", "interview"], transitions: {}, terminal: [] },
      trash_status: "trashed",
      job_kinds: ["job", "internship"],
    };
  }
  if (path.startsWith("/career/stories")) return [STORY];
  if (path.startsWith("/career/connections")) return CONNECTIONS;
  if (path.startsWith("/applications?")) return [APPLICATION];
  if (path.startsWith("/opportunities?")) return [APPLICATION, ANNOUNCEMENT];
  if (path.endsWith("/application")) return APPLICATION_DETAIL;
  if (path.endsWith("/interviews")) return [] as Interview[];
  if (path.endsWith("/salary-consistency")) {
    return { inconsistent: false, claims: [], warning: null } as SalaryConsistency;
  }
  if (path.startsWith("/sources/jobhunter/config")) return { scoring: { base: 50 }, balance: {} };
  if (path.startsWith("/sources/jobhunter/linkedin-profiles")) return [];
  if (path.startsWith("/sources/jobhunter/env")) return { linkein_allow_direct: "", proxies_file: "" };
  if (path.startsWith("/settings")) return {};
  throw new Error(`unmocked GET ${path}`);
}

function renderWorkspace(
  props: { focusStoryId: string | null; focusConnectionId: string | null } = {
    focusStoryId: null,
    focusConnectionId: null,
  },
) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <CareerWorkspace {...props} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiMock.get.mockReset();
  apiMock.put.mockReset();
  apiMock.post.mockReset();
  apiMock.get.mockImplementation(async (path: string) => mockGet(path));
});
afterEach(cleanup);

describe("CareerWorkspace", () => {
  it("hikâye düzenleyicisini 'Yeni hikâye' tıklanana kadar kapalı tutar", async () => {
    renderWorkspace();
    expect(await screen.findByText("Ölçekleme hikâyesi")).toBeTruthy();
    expect(screen.queryByLabelText("S · Durum")).toBeNull();
    expect(screen.queryByText("Hikâyeyi kaydet")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Yeni hikâye/ }));
    expect(screen.getByLabelText("S · Durum")).toBeTruthy();
    expect(screen.getByText("Hikâyeyi kaydet")).toBeTruthy();
  });

  it("deep link verilen hikâyeyi seçili ve düzenlenebilir açar", async () => {
    renderWorkspace({ focusStoryId: STORY.id, focusConnectionId: null });
    expect(await screen.findByLabelText("S · Durum")).toBeTruthy();
    expect(screen.getByText("Hikâyeyi güncelle")).toBeTruthy();
  });

  it("CSV içe aktarmada önizleme, tekrar sayısı ve yerel-only beyanı gösterir", async () => {
    const { container } = renderWorkspace();
    fireEvent.click(screen.getByRole("tab", { name: "Bağlantı ağı" }));
    expect(await screen.findByText("Ada Lovelace")).toBeTruthy();
    expect(screen.getByText(/normalize:/)).toBeTruthy();

    const input = container.querySelector('input[type="file"]');
    expect(input).toBeTruthy();
    const file = new File([CSV], "Connections.csv", { type: "text/csv" });
    fireEvent.change(input as HTMLInputElement, { target: { files: [file] } });

    expect(await screen.findByText("İçe aktarma önizlemesi")).toBeTruthy();
    await waitFor(() => expect(screen.getByText("2 satır")).toBeTruthy());
    expect(screen.getByText("1 tekrar")).toBeTruthy();
    expect(screen.getByText("1 yeni")).toBeTruthy();
    expect(screen.getAllByText(/yerel PostgreSQL/).length).toBeGreaterThan(0);
    expect(apiMock.put).not.toHaveBeenCalled();
    expect(apiMock.upload).not.toHaveBeenCalled();
  });

  it("şirket araştırmasında duyuru kaydı 'Şirket Notu' etiketi taşımaz", async () => {
    renderWorkspace();
    fireEvent.click(screen.getByRole("tab", { name: "Şirket araştırması" }));
    expect(await screen.findByText("YLSY kılavuzu")).toBeTruthy();
    expect(screen.getAllByText("Şirket Notu")).toHaveLength(1);
    expect(screen.getByText("Duyuru notu")).toBeTruthy();
    expect(screen.getByText("İlana özel not")).toBeTruthy();
  });

  it("Jobhunter ayarlarını Basit/Advanced olarak ayırır ve ham metin alanı bırakmaz", async () => {
    const { container } = renderWorkspace();
    fireEvent.click(screen.getByRole("tab", { name: "Jobhunter ayarları" }));
    expect(await screen.findByText("Basit")).toBeTruthy();
    expect(screen.getByText("Advanced")).toBeTruthy();
    expect(screen.getByText("Elenme kelimeleri")).toBeTruthy();
    expect(screen.getByText("Doğrulama")).toBeTruthy();
    expect(container.querySelectorAll("textarea")).toHaveLength(0);
  });

  it("mülakat ve ön yazı sekmelerini boş veriyle çizip çökmez", async () => {
    renderWorkspace();
    fireEvent.click(screen.getByRole("tab", { name: "Mülakat hazırlığı" }));
    expect(await screen.findByText("Planlanmış görüşme yok")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Ön yazı" }));
    expect(await screen.findByText("Ön yazı denetimi")).toBeTruthy();
  });
});
