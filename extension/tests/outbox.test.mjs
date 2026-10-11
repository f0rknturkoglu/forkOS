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
      async request() {
        return true;
      },
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

test(
  "preserves an item enqueued while a flush awaits the backend",
  { concurrency: false },
  async () => {
    const state = installChrome({
      outbox: [
        {
          client_uuid: "older",
          collection: "inbox",
          url: "https://older.example",
        },
      ],
    });
    let resolveOlderRequest;
    let markOlderRequestStarted;
    const olderRequestStarted = new Promise((resolve) => {
      markOlderRequestStarted = resolve;
    });
    let fetchCalls = 0;
    globalThis.fetch = async () => {
      fetchCalls += 1;
      if (fetchCalls === 1) {
        markOlderRequestStarted();
        return new Promise((resolve) => {
          resolveOlderRequest = resolve;
        });
      }
      throw new Error("offline");
    };

    const { enqueue, flush } = await loadOutbox();
    const olderFlush = flush();
    await olderRequestStarted;
    const newerEnqueue = enqueue({
      url: "https://newer.example",
      title: "Newer",
    });
    await settleAsyncWork();
    resolveOlderRequest({
      ok: true,
      status: 201,
      async json() {
        return { id: "canonical-result" };
      },
    });
    await Promise.all([olderFlush, newerEnqueue]);

    assert.equal(
      state.outbox.some((item) => item.url === "https://newer.example"),
      true,
      "the newer capture must remain pending if it was not sent",
    );
  },
);

test(
  "rejects non-http URLs without enqueueing or fetching",
  { concurrency: false },
  async () => {
    const state = installChrome();
    let fetchCalls = 0;
    globalThis.fetch = async () => {
      fetchCalls += 1;
      return { ok: false, status: 422 };
    };

    const { enqueue } = await loadOutbox();
    const result = await enqueue({
      url: "chrome://extensions",
      title: "Extensions",
    });

    assert.equal(fetchCalls, 0);
    assert.deepEqual(state.outbox ?? [], []);
    assert.equal(result.sent, 0);
    assert.equal(result.rejected.length, 1);
    assert.match(result.rejected[0].message, /http/i);
  },
);

test(
  "moves backend 4xx responses to failed captures",
  { concurrency: false },
  async () => {
    const state = installChrome();
    globalThis.fetch = async () => ({
      ok: false,
      status: 422,
      async text() {
        return "invalid capture";
      },
    });

    const { enqueue } = await loadOutbox();
    const result = await enqueue({
      url: "https://rejected.example",
      title: "Rejected",
    });

    assert.equal(result.sent, 0);
    assert.equal(result.pending, 0);
    assert.equal(result.rejected[0].status, 422);
    assert.equal(state.outbox.length, 0);
    assert.equal(state.failedCaptures.length, 1);
    assert.equal(state.failedCaptures[0].url, "https://rejected.example");
  },
);

test(
  "lists, retries and clears failed captures",
  { concurrency: false },
  async () => {
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
      async json() {
        return { id: "canonical-result" };
      },
    });

    const { clearFailed, failedCaptures, retryFailed } = await loadOutbox();
    assert.deepEqual(await failedCaptures(), [failed]);

    const result = await retryFailed();
    assert.equal(result.sent, 1);
    assert.deepEqual(state.failedCaptures, []);
    assert.deepEqual(state.outbox, []);

    state.failedCaptures = [failed];
    await assert.rejects(clearFailed(), /onay/);
    await clearFailed(true);
    assert.deepEqual(state.failedCaptures, []);
  },
);

test(
  "enqueues and flushes job opportunities to /opportunities endpoint",
  { concurrency: false },
  async () => {
    const state = installChrome();
    let requestedUrl = null;
    let sentBody = null;

    globalThis.fetch = async (url, options) => {
      requestedUrl = url;
      sentBody = JSON.parse(options.body);
      return {
        ok: true,
        status: 201,
        async json() {
          return { id: "job-123", title: sentBody.title };
        },
      };
    };

    const { enqueueOpportunity } = await loadOutbox();
    const result = await enqueueOpportunity({
      title: "Senior Platform Engineer",
      organization: "Acme Cloud",
      url: "https://jobs.example/senior-platform",
      remote: "remote",
      location: "Berlin",
      compensation: "€80k - €100k",
      notes: "Tavsiye edilen pozisyon",
    });

    assert.equal(result.sent, 1);
    assert.equal(result.pending, 0);
    assert.match(requestedUrl, /\/opportunities$/);
    assert.equal(sentBody.kind, "job");
    assert.equal(sentBody.title, "Senior Platform Engineer");
    assert.equal(sentBody.organization, "Acme Cloud");
    assert.equal(sentBody.remote, "remote");
    assert.equal(sentBody.status, "discovered");
    assert.equal(state.outbox.length, 0);
  },
);

test(
  "enqueues and flushes todos to /todos endpoint",
  { concurrency: false },
  async () => {
    const state = installChrome();
    let requestedUrl = null;
    let sentBody = null;

    globalThis.fetch = async (url, options) => {
      requestedUrl = url;
      sentBody = JSON.parse(options.body);
      return {
        ok: true,
        status: 201,
        async json() {
          return { id: "todo-123", title: sentBody.title };
        },
      };
    };

    const { enqueueTodo } = await loadOutbox();
    const result = await enqueueTodo({
      title: "Review PR #42",
      priority: 1,
    });

    assert.equal(result.sent, 1);
    assert.equal(result.pending, 0);
    assert.match(requestedUrl, /\/todos$/);
    assert.equal(sentBody.title, "Review PR #42");
    assert.equal(sentBody.priority, 1);
    assert.equal(state.outbox.length, 0);
  },
);

test(
  "enqueues and flushes notes to /obsidian/capture endpoint",
  { concurrency: false },
  async () => {
    const state = installChrome();
    let requestedUrl = null;
    let sentBody = null;

    globalThis.fetch = async (url, options) => {
      requestedUrl = url;
      sentBody = JSON.parse(options.body);
      return {
        ok: true,
        status: 201,
        async json() {
          return { id: "note-123", title: sentBody.title };
        },
      };
    };

    const { enqueueNote } = await loadOutbox();
    const result = await enqueueNote({
      title: "Architecture Decisions",
      body_text: "Single bookmark table for inbox and library.",
      folder: "system",
      tags: ["architecture"],
      relate_to: "d4050e09-428b-43ea-b76d-4fe872975b47",
    });

    assert.equal(result.sent, 1);
    assert.equal(result.pending, 0);
    assert.match(requestedUrl, /\/obsidian\/capture$/);
    assert.equal(sentBody.title, "Architecture Decisions");
    assert.equal(sentBody.body, "Single bookmark table for inbox and library.");
    assert.equal(sentBody.folder, "system");
    assert.deepEqual(sentBody.tags, ["architecture"]);
    assert.ok(sentBody.client_uuid);
    assert.equal(sentBody.relate_to, "d4050e09-428b-43ea-b76d-4fe872975b47");
    assert.equal(state.outbox.length, 0);
  },
);

test(
  "enqueues and flushes bookmarks with pocket metadata to /capture endpoint",
  { concurrency: false },
  async () => {
    const state = installChrome();
    let requestedUrl = null;
    let sentBody = null;

    globalThis.fetch = async (url, options) => {
      requestedUrl = url;
      sentBody = JSON.parse(options.body);
      return {
        ok: true,
        status: 201,
        async json() {
          return { id: "bm-pocket-1", title: sentBody.title };
        },
      };
    };

    const { enqueue } = await loadOutbox();
    const result = await enqueue({
      url: "https://blog.example.com/deep-dive",
      title: "Deep Dive into Multi-Agent Architecture",
      collection: "read_later",
      hero_image_url: "https://blog.example.com/cover.png",
      favicon_url: "https://blog.example.com/favicon.ico",
      reading_time_min: 7,
      author: "Dr. Alice Turing",
    });

    assert.equal(result.sent, 1);
    assert.equal(result.pending, 0);
    assert.match(requestedUrl, /\/capture$/);
    assert.equal(sentBody.title, "Deep Dive into Multi-Agent Architecture");
    assert.equal(sentBody.hero_image_url, "https://blog.example.com/cover.png");
    assert.equal(sentBody.favicon_url, "https://blog.example.com/favicon.ico");
    assert.equal(sentBody.reading_time_min, 7);
    assert.equal(sentBody.author, "Dr. Alice Turing");
    assert.equal(sentBody.collection, "read_later");
    assert.equal(state.outbox.length, 0);
  },
);

test(
  "Vault failures preserve note content and stable retry identity",
  { concurrency: false },
  async () => {
    const state = installChrome();
    globalThis.fetch = async () => ({ ok: false, status: 503 });
    const { enqueueNote, flush, retryFailed } = await loadOutbox();
    const note = {
      title: "Keep",
      body_text: "Do not lose",
      tags: ["important"],
    };
    await enqueueNote(note);
    assert.equal(state.outbox.length, 1);
    const identity = state.outbox[0].client_uuid;
    globalThis.fetch = async () => ({
      ok: false,
      status: 422,
      async text() {
        return "invalid relationship";
      },
    });
    await flush();
    assert.equal(state.outbox.length, 0);
    assert.equal(state.failedCaptures[0].body_text, note.body_text);
    assert.equal(state.failedCaptures[0].client_uuid, identity);
    globalThis.fetch = async (url, options) => {
      assert.match(url, /\/obsidian\/capture$/);
      assert.equal(JSON.parse(options.body).client_uuid, identity);
      return {
        ok: true,
        status: 201,
        async json() {
          return { id: "canonical-result" };
        },
      };
    };
    await retryFailed();
    await flush();
    assert.equal(state.outbox.length, 0);
    assert.equal(state.failedCaptures.length, 0);
  },
);

test(
  "own receipt cannot borrow success from an older capture",
  { concurrency: false },
  async () => {
    const state = installChrome({
      outbox: [{ client_uuid: "old", url: "https://old.test", title: "Old" }],
    });
    let calls = 0;
    globalThis.fetch = async () =>
      ++calls === 1
        ? { ok: true, status: 201, json: async () => ({ id: "old-result" }) }
        : { ok: false, status: 422, text: async () => "invalid" };
    const { enqueue } = await loadOutbox();
    const result = await enqueue({ url: "https://new.test", title: "New" });
    assert.equal(result.sent, 1);
    assert.equal(result.capture.state, "rejected");
    assert.equal(state.failedCaptures.length, 1);
  },
);
test(
  "lost response survives worker restart and preserves the original UUID",
  { concurrency: false },
  async () => {
    const state = installChrome();
    let identity;
    globalThis.fetch = async (_url, options) => {
      identity = JSON.parse(options.body).client_uuid;
      throw new Error("response lost after commit");
    };
    let worker = await loadOutbox();
    const first = await worker.enqueueTodo({ title: "Once" });
    assert.equal(first.capture.state, "unknown_delivery");
    worker = await loadOutbox();
    globalThis.fetch = async (_url, options) => {
      assert.equal(JSON.parse(options.body).client_uuid, identity);
      return {
        ok: true,
        status: 201,
        headers: { get: () => "true" },
        json: async () => ({ id: "same-canonical" }),
      };
    };
    await worker.flush();
    assert.equal(state.outbox.length, 0);
    assert.equal(
      (await worker.captureStatus(identity)).state,
      "already_present",
    );
  },
);
test(
  "empty notes never reach HTTP and Vault outage remains retryable",
  { concurrency: false },
  async () => {
    const state = installChrome();
    let calls = 0;
    globalThis.fetch = async () => {
      calls++;
      return { ok: false, status: 503 };
    };
    const worker = await loadOutbox();
    assert.equal(
      (await worker.enqueueNote({ title: "Empty", body_text: " " })).capture
        .state,
      "invalid_input",
    );
    assert.equal(calls, 0);
    assert.equal(
      (await worker.enqueueNote({ title: "Note", body_text: "Keep" })).capture
        .state,
      "vault_unavailable",
    );
    assert.equal(state.outbox.length, 1);
  },
);
test(
  "correction keeps old failure and creates a new identity",
  { concurrency: false },
  async () => {
    const state = installChrome({
      failedCaptures: [
        {
          client_uuid: "old-failure",
          type: "todo",
          title: "Bad",
          http_status: 422,
        },
      ],
    });
    globalThis.fetch = async () => {
      throw new Error("offline");
    };
    const worker = await loadOutbox();
    const result = await worker.replaceFailed("old-failure", {
      title: "Fixed",
    });
    assert.notEqual(result.capture.client_uuid, "old-failure");
    assert.equal(
      state.failedCaptures[0].replacement_id,
      result.capture.client_uuid,
    );
    assert.equal(state.outbox[0].title, "Fixed");
  },
);
