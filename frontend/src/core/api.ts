const BASE = "/api";

const GET_TIMEOUT_MS = 30_000;
const WRITE_TIMEOUT_MS = 60_000;

export class ApiError extends Error {
  /** Hata govdesinin ham metni; programatik cikarim icin (ornek: duplicate
   *  yanitinda existing_id). `message` kullaniciya gosterilecek metindir. */
  rawBody: string | null = null;

  constructor(
    public status: number,
    message: string,
    rawBody: string | null = null,
  ) {
    super(message);
    this.rawBody = rawBody;
  }
}

export class OfflineWriteError extends Error {
  constructor() {
    super("Çevrimdışıyken değişiklik yapılamaz; bağlantı gelince tekrar dene.");
    this.name = "OfflineWriteError";
  }
}

const isOnline = () => typeof navigator === "undefined" || navigator.onLine;

function assertOnlineWrite(): void {
  if (!isOnline()) throw new OfflineWriteError();
}

/** Hata govdesinden hem gosterilecek metni hem ham govdeyi cikarir.
 *  FastAPI hata govdesi {"detail": ...} — detail string ise o gosterilir,
 *  degilse seri hali; detail yoksa ham govde (eski davranis) korunur. */
async function errorParts(res: Response): Promise<[string, string | null]> {
  const fallback = `${res.status} ${res.statusText}`;
  const body = await res.text().catch(() => "");
  if (!body) return [fallback, null];
  try {
    const parsed = JSON.parse(body) as { detail?: unknown };
    if (typeof parsed.detail === "string") return [parsed.detail, body];
    if (parsed.detail !== undefined) return [JSON.stringify(parsed.detail), body];
  } catch {
    // body JSON degilse ham metin hem mesaj hem rawBody olur
  }
  return [body || fallback, body];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method ?? "GET";
  if (method !== "GET") assertOnlineWrite();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), method === "GET" ? GET_TIMEOUT_MS : WRITE_TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    const [message, rawBody] = await errorParts(res);
    throw new ApiError(res.status, message, rawBody);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) => request<T>(p, { method: "POST", body: JSON.stringify(body ?? {}) }),
  patch: <T>(p: string, body?: unknown) => request<T>(p, { method: "PATCH", body: JSON.stringify(body ?? {}) }),
  put: <T>(p: string, body?: unknown) => request<T>(p, { method: "PUT", body: JSON.stringify(body ?? {}) }),
  del: (p: string, body?: unknown) =>
    request<void>(p, { method: "DELETE", ...(body ? { body: JSON.stringify(body) } : {}) }),
  /** multipart -- Content-Type'i tarayici koysun, elle yazma. */
  upload: async <T>(p: string, file: File, field = "file") => {
    assertOnlineWrite();
    const form = new FormData();
    form.append(field, file);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), WRITE_TIMEOUT_MS);
    let res: Response;
    try {
      res = await fetch(`${BASE}${p}`, { method: "POST", body: form, signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
    if (!res.ok) {
      const [message, rawBody] = await errorParts(res);
      throw new ApiError(res.status, message, rawBody);
    }
    return res.json() as Promise<T>;
  },
};

/** Query string'i undefined alanlari atarak kurar. */
export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
}
