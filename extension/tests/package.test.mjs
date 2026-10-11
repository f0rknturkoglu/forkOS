import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync, existsSync } from "node:fs";
import { extractAnnouncement } from "../extractor.js";
import { normalizeApiBase, normalizeWebBase } from "../config.js";
import { deliveryText } from "../delivery.js";
test("MV3 manifest resources and real PNG dimensions are valid", () => {
  const root = new URL("../", import.meta.url);
  const manifest = JSON.parse(readFileSync(new URL("manifest.json", root)));
  assert.equal(manifest.manifest_version, 3);
  assert.equal(manifest.content_scripts, undefined);
  for (const path of [
    manifest.background.service_worker,
    manifest.action.default_popup,
    manifest.options_ui.page,
    ...Object.values(manifest.icons),
  ])
    assert.ok(existsSync(new URL(path, root)), path);
  for (const [size, path] of Object.entries(manifest.icons)) {
    const png = readFileSync(new URL(path, root));
    assert.equal(png.subarray(1, 4).toString(), "PNG");
    assert.equal(png.readUInt32BE(16), Number(size));
    assert.equal(png.readUInt32BE(20), Number(size));
  }
});
test("public or credentialed API/web origins cannot be configured", () => {
  for (const url of [
    "https://public.example:8787",
    "http://secret@127.0.0.1:8787",
    "http://127.0.0.1.evil.test:8787",
  ]) {
    assert.throws(() => normalizeApiBase(url));
    assert.throws(() => normalizeWebBase(url));
  }
  assert.equal(
    normalizeWebBase("http://127.0.0.1:5199"),
    "http://127.0.0.1:5199",
  );
});
test("academic metadata leaves unknown deadlines and exam evidence absent", () => {
  const result = extractAnnouncement(
    {
      title: "Yüksek lisans duyurusu",
      scripts: [
        JSON.stringify({
          "@type": "NewsArticle",
          datePublished: "2026-10-01T10:00:00+03:00",
          publisher: { name: "University" },
        }),
      ],
    },
    "https://university.test/announcement",
  );
  assert.equal(result.organization, "University");
  assert.equal(result.deadline_at, null);
  assert.equal(result.published_at, "2026-10-01T10:00:00+03:00");
  assert.equal(result.official_document_url, null);
});
test("popup feedback follows selected receipt, never aggregate success", () => {
  assert.match(
    deliveryText({
      sent: 10,
      pending: 0,
      capture: { state: "permanent_conflict" },
    }),
    /çakışması/,
  );
  assert.match(
    deliveryText({ sent: 0, capture: { state: "already_present" } }),
    /Zaten/,
  );
});
