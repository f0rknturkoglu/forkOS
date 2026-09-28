// @vitest-environment jsdom
/**
 * Erişilebilirlik sözleşmeleri (Faz 9).
 *
 * Kapsam:
 *  - rozetli sekme adı tek parça okunur ("İşler, 12 kayıt") ve `aria-controls`
 *    panel bağını yazar; ok tuşu gezinmesi bozulmaz,
 *  - `role="dialog"` popover açılışta odağı panele taşır, Tab panelden kaçmaz,
 *    Escape ile kapanınca odağı tetikleyiciye iade eder,
 *  - satır başına yinelenen yenileme düğmeleri kaynak adını içerir.
 */
import type * as UiModule from "@/core/ui";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useRef, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { sourceLabel } from "@/core/labels";
import { Popover, Tabs } from "@/core/ui";

const harness = vi.hoisted(() => {
  const catalog = [
    {
      id: "forkjob_core:linkedin",
      interval_minutes: 720,
      kind: "job",
      class: "slow_optin",
      estimated_seconds: 300,
    },
    {
      id: "forkjob_core:eures",
      interval_minutes: 1440,
      kind: "job",
      class: "normal",
      estimated_seconds: 120,
    },
  ];
  const runs = [
    {
      id: "run-1",
      source: "forkjob_core:eures",
      status: "ok",
      items_found: 4,
      error: null,
      error_kind: null,
      batch_id: null,
      started_at: "2026-09-13T08:00:00Z",
      finished_at: "2026-09-13T08:00:10Z",
    },
  ];
  const coverage = [
    {
      source: "forkjob_core:linkedin",
      kind: "job",
      class: "slow_optin",
      category: null,
      official: null,
      url: null,
      parser_version: null,
      last_status: "error",
      last_run_at: "2026-09-12T08:00:00Z",
      last_success_at: null,
      last_new_content_at: null,
      avg_publish_interval_days: null,
      consecutive_empty: 0,
      last_error: "zaman aşımı",
      last_error_kind: "network",
      circuit_open: false,
      consecutive_failures: 1,
      tracked: true,
    },
    {
      source: "forkjob_core:eures",
      kind: "job",
      class: "normal",
      category: null,
      official: null,
      url: null,
      parser_version: null,
      last_status: "ok",
      last_run_at: "2026-09-13T08:00:00Z",
      last_success_at: "2026-09-13T08:00:00Z",
      last_new_content_at: "2026-09-13T08:00:00Z",
      avg_publish_interval_days: null,
      consecutive_empty: 0,
      last_error: null,
      last_error_kind: null,
      circuit_open: false,
      consecutive_failures: 0,
      tracked: true,
    },
  ];
  const cache = {
    dir: "/tmp/cache",
    mode: "on",
    files: 2,
    bytes: 2048,
    oldest: null,
    hosts: {},
    max_bytes: 1024 ** 3,
    max_age_seconds: 604_800,
  };
  const get = vi.fn(async (path: string) => {
    if (path === "/sources/catalog") return catalog;
    if (path === "/sources/runs") return runs;
    if (path === "/sources/coverage") return coverage;
    if (path === "/sources/cache") return cache;
    if (path === "/sources/sync") return { active: null, running: [], sources: [], last_completed: null };
    return [];
  });
  const post = vi.fn(async () => ({
    batch_id: "b1",
    queued: 1,
    total_sources: 1,
    estimated_seconds: 10,
    mode: "general",
  }));
  return { get, post };
});

vi.mock("@/core/api", () => ({
  api: { get: harness.get, post: harness.post, patch: vi.fn(), del: vi.fn() },
}));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/core/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof UiModule>();
  return { ...actual, useToast: () => ({ push: vi.fn() }) };
});

import { SourcesWorkspace } from "@/modules/sources/SourcesWorkspace";

afterEach(() => {
  cleanup();
  harness.get.mockClear();
  harness.post.mockClear();
});

describe("Tabs erişilebilir adları", () => {
  it("rozeti ayırarak sekme adını tek parça okur ve panel bağını yazar", () => {
    const onChange = vi.fn();
    render(
      <Tabs
        value="jobs"
        onChange={onChange}
        ariaLabel="Fırsat çalışma alanları"
        panelId={(id) => `panel-${id}`}
        items={[
          { id: "jobs", label: "İşler", badge: 12 },
          { id: "announcements", label: "Duyurular", badge: 3 },
        ]}
      />,
    );

    const jobs = screen.getByRole("tab", { name: "İşler, 12 kayıt" });
    expect(jobs.getAttribute("aria-selected")).toBe("true");
    expect(jobs.getAttribute("aria-controls")).toBe("panel-jobs");
    // Rozet sayısı ayrı bir öge olarak okunmaz; ad tek parçadır.
    expect(screen.queryByRole("tab", { name: "İşler 12" })).toBeNull();

    // Ok tuşu gezinmesi korunur ve hedef sekme odaklanır.
    const announcements = screen.getByRole("tab", { name: "Duyurular, 3 kayıt" });
    fireEvent.keyDown(screen.getByRole("tablist"), { key: "ArrowRight" });
    expect(onChange).toHaveBeenCalledWith("announcements");
    expect(document.activeElement).toBe(announcements);
  });

  it("dar ekranda kırpılmaz: şerit yatay kayar, sekmeler daralmaz", () => {
    render(
      <Tabs
        value="a"
        onChange={vi.fn()}
        ariaLabel="Sekmeler"
        items={[
          { id: "a", label: "Bir" },
          { id: "b", label: "İki" },
          { id: "c", label: "Üç" },
        ]}
      />,
    );

    // jsdom yerleşim ölçmez; taşma sözleşmesi sınıf düzeyinde tutulur:
    // kaydırma kabı + daralmayan sekme = hiçbir sekme kırpılmaz.
    expect(screen.getByRole("tablist").className).toContain("overflow-x-auto");
    for (const tab of screen.getAllByRole("tab")) expect(tab.className).toContain("shrink-0");
  });
});

function DialogPopoverHarness() {
  const [open, setOpen] = useState(false);
  const anchor = useRef<HTMLButtonElement>(null);
  return (
    <>
      <button ref={anchor} type="button" onClick={() => setOpen(true)}>
        Paneli aç
      </button>
      <Popover open={open} onClose={() => setOpen(false)} anchorRef={anchor} role="dialog" ariaLabel="Kaynak paneli">
        <button type="button">Birinci</button>
        <button type="button">İkinci</button>
      </Popover>
    </>
  );
}

describe("Popover odak yönetimi", () => {
  it("açılışta odağı panele taşır, Tab panelden kaçmaz, Escape odağı iade eder", () => {
    render(<DialogPopoverHarness />);
    const trigger = screen.getByRole("button", { name: "Paneli aç" });
    trigger.focus();
    fireEvent.click(trigger);

    expect(screen.getByRole("dialog", { name: "Kaynak paneli" })).toBeTruthy();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Birinci" }));

    // Son ögeden Tab: odak panelin ilk ögesine döner, dışarı kaçmaz.
    screen.getByRole("button", { name: "İkinci" }).focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Birinci" }));

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });
});

function renderWorkspace() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SourcesWorkspace />
    </QueryClientProvider>,
  );
}

describe("Kaynak satırı düğme adları", () => {
  it("yinelenen yenileme düğmeleri kaynak adını taşır", async () => {
    renderWorkspace();

    // Her satırın düğmesi ayrı ad alır: iki kayıt, iki farklı ad.
    expect(await screen.findAllByRole("button", { name: /— yenile$/ })).toHaveLength(2);
    for (const id of ["forkjob_core:linkedin", "forkjob_core:eures"]) {
      expect(screen.getByRole("button", { name: `${sourceLabel(id)} — yenile` })).toBeTruthy();
    }
  });

  it("yenileme hata verse de satır düğmesi kilitli kalmaz", async () => {
    harness.post.mockRejectedValueOnce(new Error("ağ hatası"));
    renderWorkspace();

    const name = `${sourceLabel("forkjob_core:eures")} — yenile`;
    fireEvent.click(await screen.findByRole("button", { name }));

    await waitFor(() => expect(harness.post).toHaveBeenCalledWith("/sources/forkjob_core%3Aeures/refresh"));
    // pending hata sonrası temizlenir; düğme yeniden kullanılabilir olur.
    await waitFor(() => expect((screen.getByRole("button", { name }) as HTMLButtonElement).disabled).toBe(false));
  });
});
