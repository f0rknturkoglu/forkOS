// @vitest-environment jsdom
/**
 * Paylaşılan kaynak yüzeyinin dürüstlük sözleşmeleri.
 *
 * Kapsam:
 *  - genel yenileme `{mode:"general"}`, tam tarama `{mode:"full"}` gönderir
 *    (boş gövde ASLA; "Tümünü çek" diye bir etiket yok),
 *  - katalog düştüğünde "0 kaynak" yazılmaz; alınamadı + yeniden dene denir,
 *  - kapsam düştüğünde sağlık özeti "bilinmiyor" olur, "sorun yok" DENMEZ,
 *  - kullanıcının kapattığı kaynak ("kapalı") tehlike olarak gösterilmez,
 *  - sorunlu satır hata sınıfını ve devre durumunu gösterir; tanılama paketi
 *    yalnız sorunlu satırda kopyalanabilir,
 *  - koşu geçmişi düşse bile yenileme ve katalog çalışmaya devam eder,
 *  - önbellek işlemleri ÇEVRİMDIŞI da yapılabilir (yerel disk işi), çekim yapılamaz.
 */
import type * as HooksModule from "@/lib/hooks";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { confirmDialog } from "@/core/dialog";
import { useOnline } from "@/lib/hooks";
import { SourcesWorkspace } from "./SourcesWorkspace";

const catalog = [
  { id: "jobhunter:eures", interval_minutes: 1440, kind: "job", class: "normal", estimated_seconds: 120 },
  { id: "jobhunter:linkedin", interval_minutes: 720, kind: "job", class: "slow_optin", estimated_seconds: 180 },
  { id: "announcement:ylsy", interval_minutes: 4320, kind: "announcement", class: "normal", estimated_seconds: 30 },
];

const coverageBase = {
  kind: "job",
  category: null,
  official: null,
  url: null,
  parser_version: "v3",
  last_success_at: "2026-09-21T08:00:00Z",
  last_new_content_at: "2026-09-21T08:00:00Z",
  avg_publish_interval_days: 2.5,
  consecutive_empty: 0,
  circuit_open: false,
  consecutive_failures: 0,
  tracked: true,
  retry_at: null,
};

const coverage = [
  {
    ...coverageBase,
    source: "jobhunter:eures",
    class: "normal",
    last_status: "ok",
    last_run_at: "2026-09-21T08:00:00Z",
    last_error: null,
    last_error_kind: null,
  },
  {
    ...coverageBase,
    source: "jobhunter:linkedin",
    class: "slow_optin",
    last_status: "error",
    last_run_at: "2026-09-22T08:00:00Z",
    last_error: "429 Too Many Requests — portal gecici olarak istekleri reddediyor",
    last_error_kind: "http_429",
    circuit_open: true,
    consecutive_failures: 4,
    retry_at: "2026-09-22T12:00:00Z",
  },
  {
    ...coverageBase,
    source: "announcement:ylsy",
    class: "normal",
    last_status: "disabled",
    last_run_at: "2026-09-20T08:00:00Z",
    last_error: null,
    last_error_kind: null,
    last_success_at: null,
    last_new_content_at: null,
  },
];

const runs = [
  {
    id: "run-1",
    source: "jobhunter:eures",
    status: "ok",
    items_found: 4,
    error: null,
    error_kind: null,
    started_at: "2026-09-21T08:00:00Z",
    finished_at: "2026-09-21T08:00:09Z",
  },
];

const cacheStats = {
  dir: "/cache",
  mode: "on",
  files: 12,
  bytes: 4096,
  oldest: null,
  hosts: {},
  max_bytes: 1024 ** 3,
  max_age_seconds: 604_800,
};

const idleSync = { active: null, last_completed: null, running: [], sources: [] };

const harness = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  clipboard: { writeText: vi.fn(async (_text: string) => {}) },
}));

vi.mock("@/core/api", () => ({
  api: { get: harness.get, post: harness.post, patch: vi.fn(), del: vi.fn() },
}));
vi.mock("@/core/dialog", () => ({ confirmDialog: vi.fn(async () => true) }));
vi.mock("@/lib/hooks", async (importOriginal) => {
  const actual = await importOriginal<typeof HooksModule>();
  return { ...actual, useOnline: vi.fn(() => true) };
});

function respondWith(overrides: Record<string, unknown>) {
  harness.get.mockImplementation(async (path: string) => {
    if (path in overrides) {
      const value = overrides[path];
      // Tembel hata: reddedilmiş söz test kurulumunda değil, çağrı anında oluşsun.
      return typeof value === "function" ? (value as () => unknown)() : value;
    }
    if (path === "/sources/catalog") return catalog;
    if (path === "/sources/coverage") return coverage;
    if (path === "/sources/runs") return runs;
    if (path === "/sources/cache") return cacheStats;
    if (path === "/sources/sync") return idleSync;
    return [];
  });
}

function renderSurface() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SourcesWorkspace framing="system" />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  harness.get.mockReset();
  harness.post.mockReset();
  harness.clipboard.writeText.mockClear();
  Object.assign(navigator, { clipboard: harness.clipboard });
  vi.mocked(useOnline).mockReturnValue(true);
  vi.mocked(confirmDialog).mockResolvedValue(true);
  respondWith({});
});

afterEach(() => cleanup());

describe("yenileme niyeti", () => {
  it("genel yenileme mode=general, tam tarama mode=full gönderir", async () => {
    renderSurface();
    // Katalog hazır olmadan yenileme kapsamı hesaplanmaz; düğme o an açılır.
    await screen.findByTitle("2 kaynak · ~3 dk");
    fireEvent.click(screen.getByRole("button", { name: "Kritik + normal yenile" }));

    await waitFor(() => expect(harness.post).toHaveBeenCalledWith("/sources/refresh", { mode: "general" }));
    // "Tümünü çek" diye bir etiket yok; genel yenileme kapsamı yazar.
    expect(screen.queryByText(/Tümünü çek/)).toBeNull();
    expect(screen.getByTitle("2 kaynak · ~3 dk")).toBeTruthy();

    harness.post.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Tam tarama" }));
    await waitFor(() => expect(harness.post).toHaveBeenCalledWith("/sources/refresh", { mode: "full" }));
    // Onay metni yavaş/isteğe bağlı kaynakların dahil olduğunu söyler.
    expect(vi.mocked(confirmDialog).mock.calls[0][0].body).toContain("DAHİL");
  });
});

describe("satır yenilemesi", () => {
  it("kaynağa ayrılmış ucu çağırır (toplu gövde göndermez)", async () => {
    renderSurface();
    fireEvent.click(await screen.findByRole("button", { name: "eures — yenile" }));

    await waitFor(() => expect(harness.post).toHaveBeenCalledWith("/sources/jobhunter%3Aeures/refresh"));
    // Satır tek başına çekilir: toplu uç (`/sources/refresh`) kullanılmaz.
    expect(harness.post).not.toHaveBeenCalledWith("/sources/refresh", expect.anything());
  });
});

describe("katalog düştüğünde", () => {
  it("alınamadı der, '0 kaynak' yazmaz ve yeniden dene sunar", async () => {
    respondWith({ "/sources/catalog": () => Promise.reject(new Error("ağ hatası")) });
    renderSurface();

    expect(await screen.findByText("Kaynak kataloğu alınamadı.")).toBeTruthy();
    expect(document.body.textContent).not.toContain("0 kaynak");
    expect(screen.getByRole("button", { name: /Yeniden dene/ })).toBeTruthy();
    // Katalog yokken yenileme kapsamı hesaplanamaz: düğme kapalı.
    expect((screen.getByRole("button", { name: /Kritik \+ normal yenile/ }) as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("kapsam düştüğünde", () => {
  it("sağlık özetinin bilinmediğini söyler ve 'sorun yok' demez", async () => {
    respondWith({ "/sources/coverage": () => Promise.reject(new Error("ağ hatası")) });
    renderSurface();

    expect(await screen.findByText("Kaynak sağlık özeti alınamadı.")).toBeTruthy();
    // Hem sağlık özeti hem kapsam matrisi aynı dürüst cümleyi kurar.
    expect(screen.getAllByText(/sorun olmadığı anlamına gelmez/).length).toBeGreaterThan(0);
    expect(screen.queryByText("Şu anda ilgi isteyen kaynak yok.")).toBeNull();
    expect(screen.getByText("Durum kısmen bilinmiyor")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: /Yeniden dene/ }).length).toBeGreaterThan(0);
  });
});

describe("kullanıcının kapattığı kaynak", () => {
  it("'kapalı' gösterilir ve tehlike tonu almaz", async () => {
    // Kapsamda yalnız sağlıklı + kapalı kaynak var: sorun yok, sakin satır görünür.
    respondWith({ "/sources/coverage": [coverage[0], coverage[2]] });
    renderSurface();
    const chip = await screen.findByText("kapalı");

    expect(chip.className).not.toMatch(/danger/);
    expect(screen.getByText("Şu anda ilgi isteyen kaynak yok.")).toBeTruthy();
    expect(screen.getByText("1 sağlıklı")).toBeTruthy();
  });
});

describe("sorunlu satır", () => {
  it("hata sınıfını ve devre durumunu gösterir", async () => {
    renderSurface();
    await screen.findByText("kapalı");

    expect(screen.getAllByText("429").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/devre açık/).length).toBeGreaterThan(0);
    expect(screen.getByText("1 sağlıklı · 1 ilgi istiyor")).toBeTruthy();
  });

  it("tanılama paketini yalnız sorunlu satırda kopyalatır", async () => {
    renderSurface();
    // Tek sorunlu kaynak → tek kopyalama düğmesi; sağlıklı satırlar temiz.
    const copy = await screen.findAllByRole("button", { name: "Bu kaynağın teşhisini kopyala" });
    expect(copy).toHaveLength(1);

    fireEvent.click(copy[0]);
    await waitFor(() => expect(harness.clipboard.writeText).toHaveBeenCalledTimes(1));
    const bundle = harness.clipboard.writeText.mock.calls[0][0];
    expect(bundle).toContain("# forkOS Source Diagnostics");
    expect(bundle).toContain("Source: jobhunter:linkedin");
    expect(bundle).toContain("Circuit open: true");
    expect(bundle).toContain("Error kind label: 429");
  });
});

describe("bağımsız bozulma", () => {
  it("koşu geçmişi düşse bile katalog ve yenileme çalışır", async () => {
    respondWith({ "/sources/runs": () => Promise.reject(new Error("ağ hatası")) });
    renderSurface();

    expect(await screen.findByText("Koşu geçmişi alınamadı.")).toBeTruthy();
    expect(screen.getByText("eures")).toBeTruthy();
    expect((screen.getByRole("button", { name: /Kritik \+ normal yenile/ }) as HTMLButtonElement).disabled).toBe(false);
  });
});

describe("çevrimdışı", () => {
  it("çekimi kapatır ama yerel önbellek işlemlerini açık tutar", async () => {
    vi.mocked(useOnline).mockReturnValue(false);
    renderSurface();

    await screen.findByText("kapalı");
    expect((screen.getByRole("button", { name: /Kritik \+ normal yenile/ }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/Çevrimdışı: kaynak çekimi başlatılamaz/)).toBeTruthy();
    expect((screen.getByRole("button", { name: /Bütçeye indir/ }) as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: "Önbelleği temizle" }) as HTMLButtonElement).disabled).toBe(false);
  });
});
