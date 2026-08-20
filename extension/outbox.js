/**
 * Offline kuyruk -- bu mimarinin en kritik parcasi.
 *
 * Backend local'de calisiyor ve zamanin cogunda KAPALI olacak.
 * Kaydetme her zaman once kuyruga yazar, sonra gonderilmeye calisilir.
 * client_uuid sayesinde retry'de cift kayit olusmaz (backend idempotent).
 */
import { API_BASE } from "./config.js";

const KEY = "outbox";
const LAST_RESULT_KEY = "lastResult";

async function readQueue() {
  const { [KEY]: queue = [] } = await chrome.storage.local.get(KEY);
  return queue;
}

async function writeQueue(queue) {
  await chrome.storage.local.set({ [KEY]: queue });
  await chrome.action.setBadgeBackgroundColor({ color: queue.length ? "#b45309" : "#166534" });
  await chrome.action.setBadgeText({ text: queue.length ? String(queue.length) : "" });
}

export async function enqueue(item) {
  const queue = await readQueue();
  queue.push({ client_uuid: crypto.randomUUID(), collection: "inbox", ...item });
  await writeQueue(queue);
  return flush();
}

export async function pendingCount() {
  return (await readQueue()).length;
}

export async function lastResult() {
  const { [LAST_RESULT_KEY]: result = null } = await chrome.storage.local.get(LAST_RESULT_KEY);
  return result;
}

/**
 * Kuyrugu bosaltmayi dener.
 * Doner: { sent, pending, duplicates: [{ url, existing_id }] }
 */
export async function flush() {
  const queue = await readQueue();
  if (queue.length === 0) return { sent: 0, pending: 0, duplicates: [] };

  const remaining = [];
  const duplicates = [];
  let sent = 0;

  for (const item of queue) {
    try {
      const res = await fetch(`${API_BASE}/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(item),
      });

      if (res.ok) {
        sent++;
        const body = await res.json().catch(() => null);
        if (body?.duplicate) duplicates.push({ url: item.url, existing_id: body.existing_id });
      } else if (res.status >= 400 && res.status < 500) {
        // Kalici hata (gecersiz URL vb.) -- tekrar denemenin anlami yok, dusur.
        sent++;
        console.warn("forkOS: kayit reddedildi", res.status, item.url);
      } else {
        remaining.push(item);
      }
    } catch {
      remaining.push(item);   // backend kapali -- kuyrukta kalsin
    }
  }

  await writeQueue(remaining);
  const result = { sent, pending: remaining.length, duplicates };
  await chrome.storage.local.set({ [LAST_RESULT_KEY]: { ...result, at: Date.now() } });
  return result;
}

/** Backend ayakta mi? Popup "kuyruga alindi" mesajini buna gore gosterir. */
export async function ping() {
  try {
    const res = await fetch(`${API_BASE.replace(/\/api$/, "")}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

/** Duplicate uyarisindaki "Learning'e tasi" butonu. */
export async function moveTo(bookmarkId, collection) {
  const res = await fetch(
    `${API_BASE}/bookmarks/${bookmarkId}/collection?collection=${encodeURIComponent(collection)}`,
    { method: "PATCH" },
  );
  return res.ok;
}
