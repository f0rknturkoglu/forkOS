// @vitest-environment jsdom
/**
 * JobDetail — iş ilanı çalışma yüzeyi (Faz 4.2).
 *
 * Kapsam:
 *  - özet künyesi kaynak gözlemini (son görülme / kapandı) ve kapanma
 *    ihtimalini türetir,
 *  - uyum sekmesi üç katmanı (genel uygunluk · profil uyumu · CV
 *    değerlendirmesi) provenance'ıyla AYRI gösterir,
 *  - başvuru hattı seçimi YALNIZCA `allowed_application_transitions` sunar ve
 *    `POST /applications/{id}/transition` çağırır,
 *  - başvuru yoksa `POST /opportunities/{id}/apply` sunar,
 *  - birleşik zaman çizelgesi kronolojik render edilir.
 */
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Opportunity } from "@/core/types";

vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(({ queryKey }: { queryKey: unknown[] }) => {
    const path = queryKey.join("/");
    if (path.endsWith("timeline")) {
      return {
        data: {
          opportunity_id: "opp-1",
          entries: [
            {
              kind: "interview",
              at: "2026-09-02T10:00:00Z",
              title: "Teknik görüşme planlandı",
              detail: "Google Meet",
              status: null,
            },
            {
              kind: "discovered",
              at: "2026-08-01T10:00:00Z",
              title: "İlan keşfedildi",
              detail: null,
              status: "discovered",
            },
          ],
        },
        isLoading: false,
      };
    }
    if (path.startsWith("application")) {
      return { data: null, isLoading: false, refetch: vi.fn() };
    }
    return { data: [], isLoading: false, refetch: vi.fn() };
  }),
  useMutation: vi.fn((options: { mutationFn: (vars: unknown) => unknown }) => ({
    mutate: (vars: unknown) => void options.mutationFn(vars),
    isPending: false,
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
}));

vi.mock("@/core/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/ui")>();
  return { ...actual, useToast: () => ({ push: vi.fn() }) };
});
vi.mock("@/lib/hooks", () => ({ useOnline: () => true, useDebounced: (value: string) => value }));
vi.mock("@/core/SaveToLibrary", () => ({ useSaveToLibrary: () => ({ save: vi.fn() }) }));
vi.mock("@/app/router", () => ({ navigate: vi.fn() }));

import { api } from "@/core/api";
import { JobDetail } from "./JobDetail";

const JOB: Opportunity = {
  id: "opp-1",
  title: "Senior Platform Engineer",
  kind: "job",
  category: "cloud-security",
  organization: "Acme",
  url: "https://acme.example/jobs/1",
  status: "discovered",
  allowed_transitions: ["shortlisted", "dismissed", "archived"],
  priority: 3,
  found_at: "2026-08-01T10:00:00Z",
  published_at: "2026-07-30T10:00:00Z",
  deadline_at: "2026-09-30T10:00:00Z",
  applied_at: null,
  location: "Berlin",
  remote: "hybrid",
  compensation: "€80k–€95k",
  source: "linkedin",
  external_id: null,
  raw: {},
  score: 72,
  score_source: "forkjob-rules",
  score_computed_at: "2026-09-01T08:00:00Z",
  score_reasons: { base: 50, skills: { term: "kubernetes", where: "description", delta: 22 }, total: 72 },
  notes: null,
  trashed_at: null,
  trashed_from_status: null,
  country: "DE",
  region: "EU",
  follow_up_at: null,
  rejection_reason: null,
  profile_match_ratio: 0.5,
  skill_match: { match_ratio: 0.5, matched: ["Docker"], missing: ["Kubernetes"] },
  application_status: null,
  application_status_changed_at: null,
  allowed_application_transitions: [],
  intelligence: null,
  evaluation: null,
  source_status: "missing",
  last_seen_at: "2026-09-05T10:00:00Z",
  closed_at: null,
  official: null,
  parent_id: null,
  stage: null,
  application_start_at: null,
  application_end_at: null,
  exam_at: null,
  result_at: null,
  guide_url: null,
  apply_url: null,
  quota_total: null,
  fields: [],
};

afterEach(cleanup);

describe("JobDetail", () => {
  it("özet künyesinde kaynak gözlemini ve kapanma ihtimalini türetir", () => {
    render(<JobDetail item={JOB} />);
    expect(screen.getByText("İlan künyesi")).toBeTruthy();
    expect(screen.getByText("Kaynak durumu")).toBeTruthy();
    expect(screen.getAllByText("Kaynakta görünmüyor").length).toBe(2);
    expect(screen.getByText("Kapanma ihtimali")).toBeTruthy();
    // Kaynakta son görülme tarihi 05.09.2026; kapanma riski "Orta".
    expect(screen.getByText("Orta")).toBeTruthy();
    expect(screen.getByText("İlan son taramada kaynakta bulunamadı; kapanma ihtimali var.")).toBeTruthy();
  });

  it("uyum sekmesi üç katmanı provenance'ıyla ayrı gösterir", () => {
    render(<JobDetail item={JOB} />);
    fireEvent.click(screen.getByRole("tab", { name: "Uyum" }));

    // (a) Genel uygunluk + açıklanabilir puan bileşenleri.
    expect(screen.getByText("Genel uygunluk")).toBeTruthy();
    expect(screen.getByText("Neden bu puan?")).toBeTruthy();
    expect(screen.getByText("Temel puan")).toBeTruthy();
    expect(screen.getByText("Beceri uyumu")).toBeTruthy();
    expect(screen.getByText("kubernetes · description · +22")).toBeTruthy();
    expect(screen.getAllByText("forkjob-rules").length).toBeGreaterThan(0);

    // (b) Profil uyumu CV dosyası kullanmadığını açıkça söyler.
    expect(screen.getByText("Profil Uyumu")).toBeTruthy();
    expect(screen.getByText("CV dosyası kullanmaz")).toBeTruthy();

    // (c) CV değerlendirmesi ayrı bir katmandır; henüz çalışmadıysa yolu gösterir.
    expect(screen.getByText("CV Değerlendirmesi")).toBeTruthy();
    expect(screen.getByText("İlanı iki aşamada değerlendir")).toBeTruthy();
  });

  it("CV değerlendirmesinin sürümünü, aday belgesini ve parmak izini gösterir", () => {
    render(
      <JobDetail
        item={{
          ...JOB,
          evaluation: {
            version: "career-ops-v1",
            evaluated_at: "2026-08-02T10:00:00Z",
            source_fingerprint: "abc123def456",
            engine: "local_rules",
            candidate_source: "document",
            candidate_document_id: "11111111-2222-3333-4444-555555555555",
            candidate_document_title: "furkan-cv.pdf",
            archetype: null,
            archetype_scores: {},
            score: 25,
            recommendation: "skip",
            requirements: [],
            matches: [],
            gate: {
              job_country: "Germany",
              authorized_to_work: false,
              sponsorship_status: "no_sponsorship",
              geo_mismatch: false,
              hard_blocker: false,
              reasons: [],
            },
            notes: null,
          },
        }}
      />,
    );
    fireEvent.click(screen.getByRole("tab", { name: "Uyum" }));
    expect(screen.getByText("career-ops-v1")).toBeTruthy();
    expect(screen.getAllByText("furkan-cv.pdf").length).toBeGreaterThan(0);
    expect(screen.getByText("abc123def456")).toBeTruthy();
    // İlan, değerlendirmeden sonra yeniden görüldü → eskimiş olarak işaretlenir.
    expect(screen.getByText("İlan verisi değerlendirmeden sonra güncellendi")).toBeTruthy();
  });

  it("başvuru hattı seçimi yalnızca izinli geçişleri sunar ve applications transition çağırır", () => {
    render(
      <JobDetail
        item={{
          ...JOB,
          application_status: "applied",
          application_status_changed_at: "2026-09-01T10:00:00Z",
          allowed_application_transitions: ["interview", "rejected"],
        }}
      />,
    );
    fireEvent.click(screen.getByRole("tab", { name: "Başvuru" }));

    const select = screen.getByRole("combobox", { name: "Başvuru aşaması" });
    const options = within(select)
      .getAllByRole("option")
      .map((option) => option.textContent);
    expect(options).toEqual(["Aşamayı güncelle…", "Görüşme", "Red"]);
    expect(within(select).queryByRole("option", { name: "Teklif" })).toBeNull();

    fireEvent.change(select, { target: { value: "interview" } });
    expect(vi.mocked(api.post)).toHaveBeenCalledWith("/applications/opp-1/transition", { to: "interview" });
  });

  it("başvuru kaydı yoksa Başvur ile apply ucunu çağırır", () => {
    render(<JobDetail item={JOB} />);
    fireEvent.click(screen.getByRole("tab", { name: "Başvuru" }));
    const button = screen.getByRole("button", { name: "Başvur" });
    fireEvent.click(button);
    expect(vi.mocked(api.post)).toHaveBeenCalledWith("/opportunities/opp-1/apply", {
      cv_document_id: null,
      cover_letter: null,
    });
  });

  it("birleşik zaman çizelgesini kronolojik render eder", () => {
    render(<JobDetail item={JOB} />);
    fireEvent.click(screen.getByRole("tab", { name: "Başvuru" }));
    const timeline = screen.getByText("Zaman çizelgesi").closest("section");
    expect(timeline).toBeTruthy();
    const text = timeline?.textContent ?? "";
    expect(text).toContain("İlan keşfedildi");
    expect(text).toContain("Teknik görüşme planlandı");
    expect(text.indexOf("İlan keşfedildi")).toBeLessThan(text.indexOf("Teknik görüşme planlandı"));
  });
});
