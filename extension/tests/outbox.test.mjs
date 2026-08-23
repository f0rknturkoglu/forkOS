import assert from "node:assert/strict";
import test from "node:test";

let importCounter = 0;

function installChrome(initial = {}) {
  const state = structuredClone(initial);
  globalThis.chrome = {
    storage: {
      local: {
        async get(key) {
          return { [key]: structuredClone(state[key]) };
        },
        async set(values) {
          Object.assign(state, structuredClone(values));
        },
      },
    },
    action: {
      async setBadgeBackgroundColor() {},
      async setBadgeText() {},
    },
    permissions: {
      async request() { return true; },
    },
  };
  return state;
}

async function loadOutbox() {
  importCounter += 1;
  return import(`../outbox.js?test=${importCounter}`);
}

async function settleAsyncWork() {
  for (let turn = 0; turn < 5; turn += 1) {
    await new Promise((resolve) => setImmediate(resolve));
  }
}

test("preserves an item enqueued while a flush awaits the backend", { concurrency: false }, async () => {
  const state = installChrome({
    outbox: [{ client_uuid: "older", collection: "inbox", url: "https://older.example" }],
  });
  let resolveOlderRequest;
  let markOlderRequestStarted;
  const olderRequestStarted = new Promise((resolve) => { markOlderRequestStarted = resolve; });
  let fetchCalls = 0;
  globalThis.fetch = async () => {
    fetchCalls += 1;
    if (fetchCalls === 1) {
      markOlderRequestStarted();
      return new Promise((resolve) => { resolveOlderRequest = resolve; });
    }
    throw new Error("offline");
  };

  const { enqueue, flush } = await loadOutbox();
  const olderFlush = flush();
  await olderRequestStarted;
  const newerEnqueue = enqueue({ url: "https://newer.example", title: "Newer" });
  await settleAsyncWork();
  resolveOlderRequest({ ok: true, status: 201, async json() { return {}; } });
  await Promise.all([olderFlush, newerEnqueue]);

  assert.equal(
    state.outbox.some((item) => item.url === "https://newer.example"),
    true,
    "the newer capture must remain pending if it was not sent",
  );
});

test("rejects non-http URLs without enqueueing or fetching", { concurrency: false }, async () => {
  const state = installChrome();
  let fetchCalls = 0;
  globalThis.fetch = async () => {
    fetchCalls += 1;
    return { ok: false, status: 422 };
  };

  const { enqueue } = await loadOutbox();
  const result = await enqueue({ url: "chrome://extensions", title: "Extensions" });

  assert.equal(fetchCalls, 0);
  assert.deepEqual(state.outbox ?? [], []);
  assert.equal(result.sent, 0);
  assert.equal(result.rejected.length, 1);
  assert.match(result.rejected[0].message, /http/i);
});

test("moves backend 4xx responses to failed captures", { concurrency: false }, async () => {
  const state = installChrome();
  globalThis.fetch = async () => ({
    ok: false,
    status: 422,
    async text() { return "invalid capture"; },
  });

  const { enqueue } = await loadOutbox();
  const result = await enqueue({ url: "https://rejected.example", title: "Rejected" });

  assert.equal(result.sent, 0);
  assert.equal(result.pending, 0);
  assert.equal(result.rejected[0].status, 422);
  assert.equal(state.outbox.length, 0);
  assert.equal(state.failedCaptures.length, 1);
  assert.equal(state.failedCaptures[0].url, "https://rejected.example");
});

test("lists, retries and clears failed captures", { concurrency: false }, async () => {
  const failed = {
    client_uuid: "failed-1",
    collection: "inbox",
    url: "https://retry.example",
    title: "Retry",
    status: 422,
    message: "bad",
  };
  const state = installChrome({ failedCaptures: [failed] });
  globalThis.fetch = async () => ({
    ok: true,
    status: 201,
    async json() { return {}; },
  });

  const { clearFailed, failedCaptures, retryFailed } = await loadOutbox();
  assert.deepEqual(await failedCaptures(), [failed]);

  const result = await retryFailed();
  assert.equal(result.sent, 1);
  assert.deepEqual(state.failedCaptures, []);
  assert.deepEqual(state.outbox, []);

  state.failedCaptures = [failed];
  await clearFailed();
  assert.deepEqual(state.failedCaptures, []);
});
