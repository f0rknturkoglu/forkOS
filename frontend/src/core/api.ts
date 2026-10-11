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

/**
 * Çevrimdışı yazma guard'ı YALNIZCA GERÇEKTEN DIŞARIYA ÇIKAN uçları engeller.
 *
 * `navigator.onLine === false` "internet yok" demektir; "yerel forkOS API'si
 * kapalı" demek DEĞİLDİR. Yerel API aynı makinede çalıştığı için internetsiz
 * de ayakta olabilir: yedek almak, önbellek bakımı yapmak, ayar kaydetmek,
 * Obsidian indeksini tazelemek, görev/fırsat yazmak YEREL işlerdir ve
 * çevrimdışıyken de çalışmalıdır. Guard bu yüzden HTTP metoduna değil, UCA
 * bakar: aşağıdaki desenler dış servislere (GitHub, Google, feed/kaynak
 * siteleri, sağlayıcı API'leri) istek atan uçlardır; liste dışındaki her yol
 * çevrimdışıyken de geçer.
 */
const EXTERNAL_WRITE_PATHS: readonly RegExp[] = [
  /^\/auth\//, // GitHub OAuth akışı (dış servis)
  /^\/system\/refresh$/, // arka plan senkronu: kaynak + RSS
  /^\/sources\/refresh$/, // toplu kaynak çekimi (source_ids ile tek kaynak dahil)
  /^\/sources\/[^/]+\/refresh$/, // tek kaynak çekimi
  /^\/sources\/sync$/, // kaynak senkron batch'i (dış siteleri çeker)
  /^\/rss\/refresh-all$/, // tüm beslemeleri çek
  /^\/rss\/feeds\/[^/]+\/refresh$/, // tek beslemeyi çek
  /^\/weather\/geocode$/, // konum adı çözümü (yalnız GET olsa da burada durur)
  /^\/calendar\/sync$/, // Google Takvim çekimi
  /^\/projects\/[^/]+\/github\/issues$/, // GitHub'da issue açar
  /^\/plan\/[^/]+\/push$/, // planı Google Takvim'e iter
];

/** Yerel yazmalar çevrimdışıyken de geçer; yalnız dış uçlar reddedilir. */
function assertOnlineWrite(path: string): void {
  if (isOnline()) return;
  // Sorgu dizesi kararı değiştirmez: `/system/refresh?mode=full` de dış uçtur.
  const endpoint = path.split("?")[0];
  if (EXTERNAL_WRITE_PATHS.some((pattern) => pattern.test(endpoint))) throw new OfflineWriteError();
}

/**
 * Taşıma katmanı hataları KULLANICIYA HAM GÖSTERİLMEZ.
 *
 * `fetch` başarısız olduğunda tarayıcı "Failed to fetch" / "NetworkError" gibi
 * İngilizce, teknik bir metin üretir; API kapalıyken nginx ise bir HTML hata
 * sayfası döndürür. İkisi de ürün dili değildir. Burada tek yerde, sınırlı ve
 * Türkçe bir mesaja çevrilir (HTTP durum kodlu sunucu mesajları korunur).
 */
export const API_UNAVAILABLE_MESSAGE = "Yerel forkOS API'sine ulaşılamadı. Servislerin çalıştığını kontrol et.";
export const API_TIMEOUT_MESSAGE = "İstek zaman aşımına uğradı.";

function isAbortError(error: unknown): boolean {
  return typeof error === "object" && error !== null && (error as { name?: string }).name === "AbortError";
}

/** HTML gövde (ör. nginx 502 sayfası) mesaj olarak gösterilmez. */
function looksLikeMarkup(body: string): boolean {
  const head = body.trimStart().slice(0, 40).toLowerCase();
  return (
    head.startsWith("<!doctype") || head.startsWith("<html") || head.startsWith("<head") || head.startsWith("<center")
  );
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
    // body JSON degil: HTML ise (proxy hata sayfasi) sinirli mesaj, duz metin
    // ise (ornek: "Not Found") sunucunun kendi metni gosterilir.
    if (looksLikeMarkup(body)) return [fallback, body];
  }
  return [body || fallback, body];
}

/**
 * Yazma gövdesini kodlar. FormData multipart'tır: `JSON.stringify` onu "{}"
 * yapar ve `Content-Type: application/json` yazar; FastAPI'nin `File(...)`
 * alanları boş kalır. Bu yüzden FormData olduğu gibi taşınır (Content-Type'ı
 * multipart sınırıyla tarayıcı koyar), diğer gövdeler JSON olur.
 */
function encodeBody(body: unknown): BodyInit {
  return body instanceof FormData ? body : JSON.stringify(body ?? {});
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method ?? "GET";
  // Okumalar hiç engellenmez: çevrimdışıyken yerel API'den okumak serbesttir.
  if (method !== "GET") assertOnlineWrite(path);
  const multipart = init?.body instanceof FormData;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), method === "GET" ? GET_TIMEOUT_MS : WRITE_TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: multipart ? undefined : { "Content-Type": "application/json" },
      signal: controller.signal,
    });
  } catch (error) {
    throw new ApiError(0, isAbortError(error) ? API_TIMEOUT_MESSAGE : API_UNAVAILABLE_MESSAGE);
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
  post: <T>(p: string, body?: unknown) => request<T>(p, { method: "POST", body: encodeBody(body) }),
  patch: <T>(p: string, body?: unknown) => request<T>(p, { method: "PATCH", body: encodeBody(body) }),
  put: <T>(p: string, body?: unknown) => request<T>(p, { method: "PUT", body: encodeBody(body) }),
  del: (p: string, body?: unknown) =>
    request<void>(p, { method: "DELETE", ...(body ? { body: JSON.stringify(body) } : {}) }),
  /** multipart -- Content-Type'i tarayici koysun, elle yazma. */
  upload: async <T>(p: string, file: File, field = "file") => {
    // Yüklemeler yerel dosya içeriğidir (OPML, CSV); çevrimdışı da geçer.
    assertOnlineWrite(p);
    const form = new FormData();
    form.append(field, file);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), WRITE_TIMEOUT_MS);
    let res: Response;
    try {
      res = await fetch(`${BASE}${p}`, { method: "POST", body: form, signal: controller.signal });
    } catch (error) {
      throw new ApiError(0, isAbortError(error) ? API_TIMEOUT_MESSAGE : API_UNAVAILABLE_MESSAGE);
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
