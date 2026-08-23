import { readFile, readdir, stat } from "node:fs/promises";
import { resolve } from "node:path";

const manifest = JSON.parse(await readFile(resolve("dist/.vite/manifest.json"), "utf8"));
const entries = Object.values(manifest).filter((item) => item.isEntry && item.file.endsWith(".js"));
const limit = 500 * 1024;
const failures = [];

for (const entry of entries) {
  const file = resolve("dist", entry.file);
  const bytes = (await stat(file)).size;
  if (bytes > limit) failures.push(`${entry.file}: ${(bytes / 1024).toFixed(1)} KB`);
}

if (failures.length > 0) {
  console.error(`Uygulama giriş chunk'ı 500 KB sınırını aştı:\n${failures.join("\n")}`);
  process.exitCode = 1;
} else {
  const assetCount = (await readdir(resolve("dist/assets"))).length;
  console.log(`${entries.length} giriş chunk'ı sınır içinde; ${assetCount} asset üretildi.`);
}
