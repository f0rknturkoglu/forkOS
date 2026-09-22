#!/usr/bin/env node
/**
 * OpenAPI path'lerinden frontend'de hiç çağrılmayanları listeler (kural 17).
 *
 * Kullanim: node scripts/check-endpoint-coverage.mjs [esik]
 * Varsayilan esik: 3 -- auth yonlendirmeleri gibi tarayici tarafi uclar haric.
 * Exit 1 => esik asildi (CI kirmizi).
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "..");
const SPEC = JSON.parse(readFileSync(join(ROOT, "..", "backend", "openapi.json"), "utf8"));
const THRESHOLD = Number(process.argv[2] ?? 3);

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (entry === "node_modules" || entry === "generated" || entry === "dist") continue;
      walk(full, out);
    } else if ((full.endsWith(".ts") || full.endsWith(".tsx")) && !full.includes(".test.")) {
      out.push(full);
    }
  }
  return out;
}

const blob = walk(join(ROOT, "src")).map((f) => readFileSync(f, "utf8")).join("\n");

// Tarayici yonlendirmeleri / auth akislari disari tutulur (window.location.href).
const EXEMPT = new Set([
  "/api/auth/google/start",
  "/api/auth/google/callback",
  "/api/auth/github/start",
  "/api/auth/github/callback",
  "/api/export/json",
  // Kayit defteri sozlesmeleri (frontend tarafinda tüketilir ya da yedek etiket ureticisi var)
  "/api/registry/entity-types",
  "/api/registry/event-verbs",
  // Infra: docker healthcheck ve eklenti bu ucu kullanir
  "/health",
  // Hermes host plugin'i tarafından tüketilir; tarayıcı yazma çağrısı değildir.
  "/api/agent/lifecycle/event",
]);

function isCalled(path) {
  if (EXEMPT.has(path)) return true;
  const parts = path.replace(/^\/api/, "").split("/").filter(Boolean).map((seg) =>
    seg.startsWith("{") ? "[^/]+" : seg.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"),
  );
  // Frontend api yardimcisi BASE'i ekler: kaynakta path /api PREFIX'SIZ gorunur.
  const rel = "/" + parts.join("/");
  const apiCall = new RegExp(
    `api\\.(?:get|post|patch|put|del|upload)(?:<[^()]*>)?\\(\\s*[\`"']` + rel + `[^\`"')]*`,
  );
  if (apiCall.test(blob)) return true;
  // Helper fonksiyonlarin urettigi literal path'ler (sourceSyncHistoryApiPath gibi)
  if (blob.includes('"' + rel + '"') || blob.includes("'" + rel + "'")) return true;
  // fetch("/api/...") -- worker/offline cagrilari (api prefix'li)
  if (new RegExp(`fetch\\(\\s*[\`"'][^)]*?/api/` + rel).test(blob)) return true;
  // window.location / <a href="/api/..."> -- dogrudan tarayici uclari
  if (new RegExp(`(?:href|location\\.href)\\s*=\\s*[\`"'][^)]*?/api/` + rel).test(blob)) return true;
  return false;
}

// Calisma zamaninda template/concatenation ile kurulan cagrilar (kaynakta tam
// path gorunmez; grep ile dogrulandi). Kural 17: uclar bagli, betik goremiyor.
const DYNAMIC_KNOWN = new Set([
  "/api/opportunities/browse", // browseQuery(filters) query string ile birlestirir
  "/api/pomodoro/{pomo_id}/pause",  // api.post(`/pomodoro/${id}/${paused ? "resume" : "pause"}`)
  "/api/pomodoro/{pomo_id}/resume",
  "/api/media/assets/{asset_name}", // mediaCoverUrl assemble eder
  // Artwork proxy'si <img src> icin kurulur (shared.proxiedCover:
  // `${ARTWORK_PROXY_PATH}?url=...`), api cagrisi degil.
  "/api/media/artwork/proxy",
  "/api/export/bookmarks",          // <a href={`/api/export/${path}`}>
  "/api/export/csv",
  "/api/export/markdown",
  "/api/export/opml",
  "/api/export/ics",
  // OpportunityPage: api.post(`/opportunities/${id}/${action}`) — eylem degisken.
  "/api/opportunities/{item_id}/trash",
  "/api/opportunities/{item_id}/restore",
  // GithubPanel: `const path = \`/projects/${project.id}/github\`` sonra api.get(path)
  // ve api.post(`${path}/issues`) — path degiskeni, kaynakta tam cagri yok.
  "/api/projects/{project_id}/github",
  "/api/projects/{project_id}/github/issues",
  // DocumentsPage indir linki: href={/api/documents/${doc.id}/file} — JSX
  // ifadesi, tarayici href kalibiyla eslesmez.
  "/api/documents/{id}/file",
]);

const uncovered = Object.keys(SPEC.paths).filter((p) => !isCalled(p) && !DYNAMIC_KNOWN.has(p)).sort();
for (const u of uncovered) console.log(u);
console.error(`\nreferanssiz uc: ${uncovered.length} (esik ${THRESHOLD})`);
if (uncovered.length > THRESHOLD) {
  console.error("ESIK ASILDI — uç ya frontend'de baglanir ya silinir (kural 17).");
  process.exit(1);
}
