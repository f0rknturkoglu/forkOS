import assert from "node:assert/strict";
import test from "node:test";

let importCounter = 0;

function installChrome(initial = {}) {
  const state = structuredClone(initial);
  const requests = [];
  globalThis.chrome = {
    storage: {
      local: {
        async get(key) { return { [key]: structuredClone(state[key]) }; },
        async set(values) { Object.assign(state, structuredClone(values)); },
      },
    },
    permissions: {
      async request(permission) {
        requests.push(permission);
        return true;
      },
    },
  };
  return { requests, state };
}

async function loadConfig() {
  importCounter += 1;
  return import(`../config.js?test=${importCounter}`);
}

test("uses a validated custom Podman VM origin", { concurrency: false }, async () => {
  const { requests, state } = installChrome();
  const { getApiBase, setApiBase } = await loadConfig();

  assert.equal(
    await setApiBase("http://192.168.127.2:8787"),
    "http://192.168.127.2:8787/api",
  );
  assert.deepEqual(requests, [{ origins: ["http://192.168.127.2:8787/*"] }]);
  assert.equal(state.apiBase, "http://192.168.127.2:8787/api");
  assert.equal(await getApiBase(), state.apiBase);
});

test("rejects non-http extension targets", { concurrency: false }, async () => {
  installChrome();
  const { normalizeApiBase } = await loadConfig();

  assert.throws(() => normalizeApiBase("file:///tmp/forkos"), /http/i);
  assert.throws(() => normalizeApiBase("javascript:alert(1)"), /http/i);
});
