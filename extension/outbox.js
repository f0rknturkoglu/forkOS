/** Stable identities are persisted before HTTP. Each capture has its own receipt. */
import { getApiBase } from "./config.js";
const KEY = "outbox",
  FAILED_KEY = "failedCaptures",
  LAST_RESULT_KEY = "lastResult",
  RECEIPTS = "captureReceipts";
let storageOperation = Promise.resolve();
let activeFlush = null;
function withStorageLock(fn) {
  const run = storageOperation.then(fn, fn);
  storageOperation = run.then(
    () => undefined,
    () => undefined,
  );
  return run;
}
async function readQueue() {
  return (await chrome.storage.local.get(KEY))[KEY] ?? [];
}
async function writeQueue(queue) {
  await chrome.storage.local.set({ [KEY]: queue });
  await chrome.action.setBadgeBackgroundColor({
    color: queue.length ? "#b45309" : "#166534",
  });
  await chrome.action.setBadgeText({
    text: queue.length ? String(queue.length) : "",
  });
}
async function receipt(id, state, extra = {}) {
  return withStorageLock(async () => {
    const all = (await chrome.storage.local.get(RECEIPTS))[RECEIPTS] ?? {};
    const value = { client_uuid: id, state, ...extra, at: Date.now() };
    await chrome.storage.local.set({ [RECEIPTS]: { ...all, [id]: value } });
    return value;
  });
}
export async function captureStatus(id) {
  return (
    (await chrome.storage.local.get(RECEIPTS))[RECEIPTS]?.[id] ?? {
      client_uuid: id,
      state: "queued_offline",
    }
  );
}
function urlError(url, optional = false) {
  if (!url && optional) return null;
  try {
    const parsed = new URL(url);
    if (
      !["http:", "https:"].includes(parsed.protocol) ||
      parsed.username ||
      parsed.password ||
      url.length > 4000
    )
      throw new Error();
  } catch {
    return "Geçerli, kimlik bilgisi içermeyen bir http(s) adresi gerekli";
  }
  return null;
}
export async function enqueue(item) {
  const entry = {
    collection: "inbox",
    priority: 2,
    ...item,
    type: item.type ?? "bookmark",
    client_uuid: crypto.randomUUID(),
  };
  if (entry.type === "opportunity") {
    entry.kind ??= "job";
    entry.status ??= entry.kind === "job" ? "discovered" : "new";
  }
  let error = urlError(entry.url, entry.type !== "bookmark");
  if (!["bookmark", "todo", "note", "opportunity"].includes(entry.type))
    error = "Desteklenmeyen yakalama türü";
  if (JSON.stringify(entry).length > 60_000)
    error = "Capture en fazla 60 KB olabilir";
  if (
    entry.type !== "bookmark" &&
    (!entry.title?.trim() || entry.title.length > 500)
  )
    error = "Başlık gerekli (en fazla 500 karakter)";
  if (entry.type === "note" && !(entry.body_text ?? entry.body ?? "").trim())
    error = "Not içeriği boş olamaz";
  if (error) {
    const capture = await receipt(entry.client_uuid, "invalid_input", {
      message: error,
    });
    return {
      sent: 0,
      pending: await pendingCount(),
      duplicates: [],
      rejected: [{ url: entry.url, status: null, message: error }],
      capture,
    };
  }
  await withStorageLock(async () => {
    const queue = await readQueue();
    await writeQueue([...queue, entry]);
  });
  await receipt(entry.client_uuid, "retry_pending");
  const result = await flush();
  return { ...result, capture: await captureStatus(entry.client_uuid) };
}
export const enqueueOpportunity = (item) =>
  enqueue({ ...item, type: "opportunity" });
export const enqueueTodo = (item) => enqueue({ ...item, type: "todo" });
export const enqueueNote = (item) => enqueue({ ...item, type: "note" });
export const pendingCount = () =>
  withStorageLock(async () => (await readQueue()).length);
export async function lastResult() {
  return (
    (await chrome.storage.local.get(LAST_RESULT_KEY))[LAST_RESULT_KEY] ?? null
  );
}
export function flush() {
  if (!activeFlush)
    activeFlush = flushQueue().finally(() => {
      activeFlush = null;
    });
  return activeFlush;
}
function payloadFor(item) {
  if (item.type === "opportunity")
    return [
      "/opportunities",
      {
        client_uuid: item.client_uuid,
        title: item.title,
        kind: item.kind || "job",
        organization: item.organization || null,
        url: item.url || null,
        status:
          item.status ||
          ((item.kind || "job") === "job" ? "discovered" : "new"),
        priority: item.priority ?? 2,
        deadline_at: item.deadline_at || null,
        published_at: item.published_at || null,
        location: item.location || null,
        remote: item.remote || null,
        compensation: item.compensation || null,
        notes: item.notes || null,
        raw: item.raw || {},
      },
    ];
  if (item.type === "todo")
    return [
      "/todos",
      {
        client_uuid: item.client_uuid,
        title: item.title,
        priority: item.priority ?? 2,
        plan_day: item.plan_day || null,
        due_at: item.due_at || null,
      },
    ];
  if (item.type === "note")
    return [
      "/obsidian/capture",
      {
        client_uuid: item.client_uuid,
        title: item.title || "Not",
        body: item.body_text ?? item.body ?? "",
        tags: item.tags || [],
        relate_to: item.relate_to || null,
        source_url: item.url || null,
        folder: item.folder || "general",
        pinned: Boolean(item.pinned),
      },
    ];
  const { type: _type, ...payload } = item;
  return ["/capture", payload];
}
async function flushQueue() {
  const queue = await withStorageLock(readQueue);
  const finalized = new Set(),
    failed = [],
    duplicates = [],
    rejected = [];
  let sent = 0;
  const base = await getApiBase();
  for (const item of queue) {
    const [path, payload] = payloadFor(item);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    try {
      const res = await fetch(base + path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      if (res.ok) {
        const body = await res.json().catch(() => null);
        if (!body?.id && !body?.forkos_id) {
          // 2xx without an identifiable canonical result is not proof of delivery.
          await receipt(item.client_uuid, "unknown_delivery", {
            message:
              "Sunucu sonucu doğrulanamadı; aynı kimlikle yeniden denenecek",
          });
          continue;
        }
        sent++;
        finalized.add(item.client_uuid);
        const duplicate =
          Boolean(body.duplicate) ||
          res.headers?.get("Idempotency-Replayed") === "true";
        if (duplicate)
          duplicates.push({
            url: item.url,
            existing_id: body.existing_id ?? body.id,
          });
        await receipt(
          item.client_uuid,
          duplicate ? "already_present" : "saved",
          { result: body },
        );
      } else if (
        res.status >= 400 &&
        res.status < 500 &&
        ![408, 429].includes(res.status)
      ) {
        const message =
          (await res.text().catch(() => "")).slice(0, 300) ||
          `HTTP ${res.status}`;
        const entry = { url: item.url, status: res.status, message };
        rejected.push(entry);
        failed.push({
          ...item,
          http_status: res.status,
          message,
          failed_at: Date.now(),
        });
        finalized.add(item.client_uuid);
        await receipt(
          item.client_uuid,
          res.status === 409 ? "permanent_conflict" : "rejected",
          { message },
        );
      } else {
        await receipt(
          item.client_uuid,
          item.type === "note" && res.status === 503
            ? "vault_unavailable"
            : "retry_pending",
          { message: "Sunucu işlemi tamamlayamadı; kayıt korunuyor" },
        );
      }
    } catch {
      await receipt(item.client_uuid, "unknown_delivery", {
        message:
          "Yanıt alınamadı; aynı kimlikle güvenli yeniden deneme bekliyor",
      });
    } finally {
      clearTimeout(timer);
    }
  }
  const pending = await withStorageLock(async () => {
    const current = await readQueue();
    const remaining = current.filter(
      (item) => !finalized.has(item.client_uuid),
    );
    const previous =
      (await chrome.storage.local.get(FAILED_KEY))[FAILED_KEY] ?? [];
    await chrome.storage.local.set({ [FAILED_KEY]: [...previous, ...failed] });
    await writeQueue(remaining);
    return remaining.length;
  });
  const result = { sent, pending, duplicates, rejected };
  await chrome.storage.local.set({
    [LAST_RESULT_KEY]: { ...result, at: Date.now() },
  });
  return result;
}
export async function ping() {
  try {
    return (
      await fetch((await getApiBase()).replace(/\/api$/, "") + "/health", {
        signal: AbortSignal.timeout(3000),
      })
    ).ok;
  } catch {
    return false;
  }
}
export async function failedCaptures() {
  return (await chrome.storage.local.get(FAILED_KEY))[FAILED_KEY] ?? [];
}
export async function failedCount() {
  return (await failedCaptures()).length;
}
export async function clearFailed(confirmed = false) {
  if (!confirmed)
    throw new Error("Başarısız kayıtları silmek için açık onay gerekli");
  await chrome.storage.local.set({ [FAILED_KEY]: [] });
}
export async function retryFailed() {
  await withStorageLock(async () => {
    const failed = await failedCaptures(),
      queue = await readQueue();
    const retried = failed
      .filter((item) => !item.replacement_id)
      .map(
        ({
          http_status: _http,
          message: _message,
          failed_at: _at,
          ...item
        }) => {
          // Preserve legacy failed captures; old HTTP status used to overwrite discovery status.
          if (typeof item.status === "number") delete item.status;
          return item;
        },
      );
    await chrome.storage.local.set({
      [FAILED_KEY]: failed.filter((item) => item.replacement_id),
    });
    const ids = new Set(queue.map((item) => item.client_uuid));
    await writeQueue([
      ...queue,
      ...retried.filter((item) => !ids.has(item.client_uuid)),
    ]);
  });
  return flush();
}
export async function replaceFailed(id, replacement) {
  const prior = (await failedCaptures()).find(
    (item) => item.client_uuid === id,
  );
  if (!prior || prior.replacement_id)
    throw new Error("Düzeltilecek kayıt bulunamadı");
  // A changed payload is a new intentional capture. Keep the old failure and replacement lineage.
  const {
    http_status: _http,
    message: _msg,
    failed_at: _at,
    ...original
  } = prior;
  if (typeof original.status === "number") delete original.status;
  const result = await enqueue({ ...original, ...replacement });
  await withStorageLock(async () => {
    const failed = await failedCaptures();
    await chrome.storage.local.set({
      [FAILED_KEY]: failed.map((item) =>
        item.client_uuid === id
          ? { ...item, replacement_id: result.capture.client_uuid }
          : item,
      ),
    });
  });
  return result;
}
