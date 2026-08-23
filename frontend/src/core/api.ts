const BASE = "/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export class OfflineWriteError extends Error {
  constructor() {
    super("Çevrimdışıyken değişiklik yapılamaz; bağlantı gelince tekrar dene.");
    this.name = "OfflineWriteError";
  }
}

export const isOnline = () => typeof navigator === "undefined" || navigator.onLine;

export function assertOnlineWrite(): void {
  if (!isOnline()) throw new OfflineWriteError();
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (init?.method && init.method !== "GET") assertOnlineWrite();
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new ApiError(res.status, detail || `${res.status} ${res.statusText}`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: "POST", body: JSON.stringify(body ?? {}) }),
  patch: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: "PATCH", body: JSON.stringify(body ?? {}) }),
  put: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: "PUT", body: JSON.stringify(body ?? {}) }),
  del: (p: string) => request<void>(p, { method: "DELETE" }),
  /** multipart -- Content-Type'i tarayici koysun, elle yazma. */
  upload: async <T>(p: string, file: File, field = "file") => {
    assertOnlineWrite();
    const form = new FormData();
    form.append(field, file);
    const res = await fetch(`${BASE}${p}`, { method: "POST", body: form });
    if (!res.ok) throw new ApiError(res.status, res.statusText);
    return res.json() as Promise<T>;
  },
};

/** Query string'i undefined alanlari atarak kurar. */
export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== "",
  );
  return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
}
