export const DEFAULT_API_BASE = "http://127.0.0.1:8787/api";
export const RETRY_MINUTES = 1;

const API_BASE_KEY = "apiBase";

export function normalizeApiBase(value) {
  const candidate = String(value || "").trim();
  let url;
  try {
    url = new URL(candidate);
  } catch {
    throw new TypeError("Geçerli bir HTTP(S) forkOS adresi gerekli");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new TypeError("Yalnızca HTTP(S) forkOS adresleri destekleniyor");
  }
  url.hash = "";
  url.search = "";
  const path = url.pathname.replace(/\/+$/, "");
  url.pathname = path.endsWith("/api") ? path : `${path}/api`;
  return url.toString().replace(/\/$/, "");
}

export async function getApiBase() {
  const { [API_BASE_KEY]: saved } = await chrome.storage.local.get(API_BASE_KEY);
  if (!saved) return DEFAULT_API_BASE;
  try {
    return normalizeApiBase(saved);
  } catch {
    return DEFAULT_API_BASE;
  }
}

export async function setApiBase(value) {
  const normalized = normalizeApiBase(value);
  const origin = `${new URL(normalized).origin}/*`;
  const granted = await chrome.permissions.request({ origins: [origin] });
  if (!granted) throw new Error("Bu forkOS adresine erişim izni verilmedi");
  await chrome.storage.local.set({ [API_BASE_KEY]: normalized });
  return normalized;
}
