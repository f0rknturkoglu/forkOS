/**
 * Offline kuyruk -- bu mimarinin en kritik parcasi.
 *
 * Backend local'de calisiyor ve zamanin cogunda KAPALI olacak.
 * Kaydetme her zaman once kuyruga yazar, sonra gonderilmeye calisilir.
 * client_uuid sayesinde retry'de cift kayit olusmaz (backend idempotent).
 */
import { getApiBase } from "./config.js";

const KEY = "outbox";
const FAILED_KEY = "failedCaptures";
const LAST_RESULT_KEY = "lastResult";
let storageOperation = Promise.resolve();
let activeFlush = null;

function withStorageLock(operation) {
  const run = storageOperation.then(operation, operation);
  storageOperation = run.then(() => undefined, () => undefined);
  return run;
}

async function readQueue() {
  const { [KEY]: queue = [] } = await chrome.storage.local.get(KEY);
  return queue;
}

async function writeQueue(queue) {
  await chrome.storage.local.set({ [KEY]: queue });
  await chrome.action.setBadgeBackgroundColor({ color: queue.length ? "#b45309" : "#166534" });
  await chrome.action.setBadgeText({ text: queue.length ? String(queue.length) : "" });
}

function rejection(url, status, message) {
  return { url, status, message };
}

function invalidUrlMessage(url, isOptional = false) {
  if (!url && isOptional) return null;
  try {
    const protocol = new URL(url).protocol;
    return protocol === "http:" || protocol === "https:"
      ? null
      : "Yalnızca http(s) sayfaları destekleniyor";
  } catch {
    return "Geçerli bir http(s) adresi gerekli";
  }
}

async function saveLastResult(result) {
  await chrome.storage.local.set({ [LAST_RESULT_KEY]: { ...result, at: Date.now() } });
}

export async function enqueue(item) {
  const isJob = item.type === "opportunity";
  const urlError = invalidUrlMessage(item.url, isJob);
  if (urlError) {
    const result = {
      sent: 0,
      pending: await pendingCount(),
      duplicates: [],
      rejected: [rejection(item.url, null, urlError)],
    };
    await saveLastResult(result);
    return result;
  }

  await withStorageLock(async () => {
    const queue = await readQueue();
    const entry = isJob
      ? { client_uuid: crypto.randomUUID(), type: "opportunity", kind: "job", status: "discovered", priority: 2, ...item }
      : { client_uuid: crypto.randomUUID(), type: "bookmark", collection: "inbox", ...item };
    queue.push(entry);
    await writeQueue(queue);
  });
  return flush();
}

export async function enqueueOpportunity(jobItem) {
  return enqueue({ type: "opportunity", ...jobItem });
}

export async function pendingCount() {
  return withStorageLock(async () => (await readQueue()).length);
}

export async function lastResult() {
  const { [LAST_RESULT_KEY]: result = null } = await chrome.storage.local.get(LAST_RESULT_KEY);
  return result;
}

/**
 * Kuyrugu bosaltmayi dener.
 * Doner: { sent, pending, duplicates, rejected }
 */
export function flush() {
  if (!activeFlush) {
    activeFlush = flushQueue().finally(() => { activeFlush = null; });
  }
  return activeFlush;
}

async function flushQueue() {
  const queue = await withStorageLock(readQueue);
  if (queue.length === 0) {
    return { sent: 0, pending: 0, duplicates: [], rejected: [] };
  }

  const finalizedIds = new Set();
  const failed = [];
  const duplicates = [];
  const rejected = [];
  let sent = 0;
  const apiBase = await getApiBase();

  for (const item of queue) {
    try {
      const isJob = item.type === "opportunity";
      const targetUrl = isJob ? `${apiBase}/opportunities` : `${apiBase}/capture`;
      const payload = isJob
        ? {
            title: item.title,
            kind: item.kind || "job",
            organization: item.organization || null,
            url: item.url || null,
            status: item.status || "discovered",
            priority: item.priority ?? 2,
            deadline_at: item.deadline_at || null,
            location: item.location || null,
            remote: item.remote || null,
            compensation: item.compensation || null,
            notes: item.notes || null,
          }
        : item;
      const res = await fetch(targetUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        sent++;
        finalizedIds.add(item.client_uuid);
        const body = await res.json().catch(() => null);
        if (body?.duplicate) duplicates.push({ url: item.url, existing_id: body.existing_id });
      } else if (res.status >= 400 && res.status < 500) {
        const responseText = await res.text().catch(() => "");
        const message = responseText.trim().slice(0, 300) || `HTTP ${res.status}`;
        const entry = rejection(item.url, res.status, message);
        rejected.push(entry);
        failed.push({ ...item, ...entry, failed_at: Date.now() });
        finalizedIds.add(item.client_uuid);
        console.warn("forkOS: kayit reddedildi", res.status, item.url, message);
      }
    } catch {
      // Backend kapali -- client_uuid kuyrukta kalir.
    }
  }

  const pending = await withStorageLock(async () => {
    const currentQueue = await readQueue();
    const remaining = currentQueue.filter((item) => !finalizedIds.has(item.client_uuid));
    const values = { [KEY]: remaining };
    if (failed.length > 0) {
      const { [FAILED_KEY]: priorFailed = [] } = await chrome.storage.local.get(FAILED_KEY);
      values[FAILED_KEY] = [...priorFailed, ...failed];
    }
    await chrome.storage.local.set(values);
    await writeQueue(remaining);
    return remaining.length;
  });

  const result = { sent, pending, duplicates, rejected };
  await saveLastResult(result);
  return result;
}

/** Backend ayakta mi? Popup "kuyruga alindi" mesajini buna gore gosterir. */
export async function ping() {
  try {
    const apiBase = await getApiBase();
    const res = await fetch(`${apiBase.replace(/\/api$/, "")}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

/** Duplicate uyarisindaki "Learning'e tasi" butonu. */
export async function moveTo(bookmarkId, collection) {
  const apiBase = await getApiBase();
  const res = await fetch(
    `${apiBase}/bookmarks/${bookmarkId}/collection?collection=${encodeURIComponent(collection)}`,
    { method: "PATCH" },
  );
  return res.ok;
}

export async function failedCaptures() {
  const { [FAILED_KEY]: failed = [] } = await chrome.storage.local.get(FAILED_KEY);
  return failed;
}

export async function failedCount() {
  return (await failedCaptures()).length;
}

export async function clearFailed() {
  await chrome.storage.local.set({ [FAILED_KEY]: [] });
}

export async function retryFailed() {
  await withStorageLock(async () => {
    const failed = await failedCaptures();
    const queue = await readQueue();
    const retried = failed.map(({ status: _status, message: _message, failed_at: _at, ...item }) => item);
    await chrome.storage.local.set({ [FAILED_KEY]: [] });
    await writeQueue([...queue, ...retried]);
  });
  return flush();
}
