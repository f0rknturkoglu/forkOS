// @vitest-environment jsdom
import "@/modules";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceHeader } from "./WorkspaceHeader";

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("@/core/api", () => ({
  api: apiMock,
  qs: vi.fn(() => ""),
}));

// Durum çubuğu ve bildirim paneli bu testin konusu değil; kendi verilerini isterler.
vi.mock("@/core/StatusLed", () => ({ StatusLed: () => null }));
vi.mock("@/core/NotificationPanel", () => ({ NotificationPanel: () => null }));

vi.hoisted(() => {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => store.set(key, value),
      removeItem: (key: string) => store.delete(key),
      clear: () => store.clear(),
    },
  });
});

const IDLE = {
  status: "idle",
  scope: "standard",
  batch_id: null,
  started: false,
  started_at: null,
  finished_at: null,
  results: {},
  errors: [],
};

function renderHeader() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <WorkspaceHeader path="/opportunities" onOpenSidebar={() => {}} />
    </QueryClientProvider>,
  );
}

describe("WorkspaceHeader yenileme kapsamı", () => {
  beforeEach(() => {
    localStorage.clear();
    // Durum çubuğu ve yenileme aynı API katmanını paylaşır; yol bazlı cevap ver.
    apiMock.get.mockReset().mockImplementation((path: string) => {
      if (path.startsWith("/system/refresh")) return Promise.resolve(IDLE);
      if (path.startsWith("/sources/sync"))
        return Promise.resolve({ active: null, last_completed: null, running: [], sources: [] });
      if (path.startsWith("/sources/health")) return Promise.resolve([]);
      return Promise.resolve({});
    });
    apiMock.post.mockReset();
  });
  afterEach(cleanup);

  it("seçilen kapsamı API'ye gönderir ve tercihi hatırlar", async () => {
    apiMock.post.mockResolvedValue({ ...IDLE, status: "running", scope: "critical", started: true });
    renderHeader();

    fireEvent.click(await screen.findByRole("button", { name: "Yenileme kapsamı ve durumu" }));
    fireEvent.click(await screen.findByRole("button", { name: /Kritik kaynaklar/ }));

    await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith("/system/refresh", { scope: "critical" }));
    expect(localStorage.getItem("forkos:refresh-scope")).toBe("critical");
  });

  it("hata sonrası yenileme düğmesi yeniden kullanılabilir olur", async () => {
    apiMock.post.mockRejectedValueOnce(new Error("ağ yok"));
    renderHeader();

    const button = await screen.findByRole("button", { name: /Kaynakları yenile/ });
    fireEvent.click(button);

    await waitFor(() => expect(apiMock.post).toHaveBeenCalledTimes(1));
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));

    apiMock.post.mockResolvedValueOnce({ ...IDLE, status: "running", started: true });
    fireEvent.click(button);
    await waitFor(() => expect(apiMock.post).toHaveBeenCalledTimes(2));
  });

  it("çalışan yenilemenin kuyruk kimliğini gösterir", async () => {
    apiMock.get.mockImplementation((path: string) => {
      if (path.startsWith("/system/refresh")) {
        return Promise.resolve({
          ...IDLE,
          status: "running",
          batch_id: "abcdef12-3456-7890-abcd-ef1234567890",
          started: true,
        });
      }
      if (path.startsWith("/sources/health")) return Promise.resolve([]);
      return Promise.resolve({});
    });
    renderHeader();

    fireEvent.click(await screen.findByRole("button", { name: "Yenileme kapsamı ve durumu" }));

    expect(await screen.findByText("abcdef12")).not.toBeNull();
  });

  it("aktif kaynak çekiminin yeni kayıt sayısını başlık rozeti olarak gösterir", async () => {
    apiMock.get.mockImplementation((path: string) => {
      if (path.startsWith("/system/refresh")) return Promise.resolve(IDLE);
      if (path.startsWith("/sources/sync")) {
        return Promise.resolve({
          active: {
            id: "batch-1",
            status: "running",
            items_found: 5,
            error_sources: 0,
            progress_pct: 40,
            completed_sources: 2,
            total_sources: 5,
          },
          last_completed: null,
          running: [],
          sources: [],
        });
      }
      return Promise.resolve([]);
    });
    renderHeader();

    expect(await screen.findByLabelText("5 yeni kayıt")).not.toBeNull();
    expect(screen.getByRole("button", { name: "Kaynaklar çekiliyor: 5 yeni kayıt" })).not.toBeNull();
  });
});

describe("WorkspaceHeader kenar cubugu dugmesi", () => {
  beforeEach(() => {
    localStorage.clear();
    apiMock.get.mockReset().mockImplementation((path: string) => {
      if (path.startsWith("/system/refresh")) return Promise.resolve(IDLE);
      if (path.startsWith("/sources/sync"))
        return Promise.resolve({ active: null, last_completed: null, running: [], sources: [] });
      return Promise.resolve(null);
    });
  });
  afterEach(cleanup);

  it("daraltilmis kenar cubugunu basligin solundan geri acar", () => {
    const onToggleCollapsed = vi.fn();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <WorkspaceHeader
          path="/notes"
          onOpenSidebar={() => {}}
          sidebarCollapsed
          onToggleCollapsed={onToggleCollapsed}
        />
      </QueryClientProvider>,
    );

    const expand = screen.getByRole("button", { name: "Kenar çubuğunu genişlet" });
    expect(expand.getAttribute("aria-controls")).toBe("app-sidebar");
    fireEvent.click(expand);
    expect(onToggleCollapsed).toHaveBeenCalledOnce();
  });

  it("genis kenar cubugunda genisletme dugmesi cizilmez", () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <WorkspaceHeader path="/notes" onOpenSidebar={() => {}} />
      </QueryClientProvider>,
    );

    expect(screen.queryByRole("button", { name: "Kenar çubuğunu genişlet" })).toBeNull();
  });
});
