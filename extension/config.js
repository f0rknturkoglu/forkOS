export const DEFAULT_API_BASE = "http://127.0.0.1:8787/api";
export const RETRY_MINUTES = 1;

export const DEFAULT_WEB_BASE = "http://127.0.0.1:5173";

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
  if (!isLocalHost(url.hostname) || url.username || url.password)
    throw new TypeError(
      "Yalnız loopback veya özel ağdaki forkOS adresleri kullanılabilir",
    );
  url.hash = "";
  url.search = "";
  const path = url.pathname.replace(/\/+$/, "");
  url.pathname = path.endsWith("/api") ? path : `${path}/api`;
  return url.toString().replace(/\/$/, "");
}

export async function getApiBase() {
  const { [API_BASE_KEY]: saved } =
    await chrome.storage.local.get(API_BASE_KEY);
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

function isLocalHost(host) {
  if (["localhost", "127.0.0.1", "[::1]"].includes(host)) return true;
  const parts = host.split(".").map(Number);
  return (
    parts.length === 4 &&
    parts.every(
      (x, i) =>
        Number.isInteger(x) &&
        x >= 0 &&
        x <= 255 &&
        String(x) === host.split(".")[i],
    ) &&
    (parts[0] === 10 ||
      (parts[0] === 192 && parts[1] === 168) ||
      (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31))
  );
}
export function normalizeWebBase(value) {
  const url = new URL(String(value).trim());
  if (
    !["http:", "https:"].includes(url.protocol) ||
    !isLocalHost(url.hostname) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash
  )
    throw new TypeError("Yerel forkOS web adresi gerekli");
  return url.href.replace(/\/$/, "");
}
export async function getWebBase() {
  const { webBase } = await chrome.storage.local.get("webBase");
  try {
    return webBase ? normalizeWebBase(webBase) : DEFAULT_WEB_BASE;
  } catch {
    return DEFAULT_WEB_BASE;
  }
}
export async function setWebBase(value) {
  const webBase = normalizeWebBase(value);
  await chrome.storage.local.set({ webBase });
  return webBase;
}
