import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const schemaPath = resolve(root, "../backend/openapi.json");
const outputPath = resolve(root, "src/generated/api-schema.ts");
const check = process.argv.includes("--check");

const nodes = await openapiTS(pathToFileURL(schemaPath));
const output = `${astToString(nodes).trimEnd()}\n`;

if (check) {
  const current = await readFile(outputPath, "utf8").catch(() => "");
  if (current !== output) {
    console.error("API sözleşmeleri güncel değil. npm run api:generate çalıştırın.");
    process.exitCode = 1;
  }
} else {
  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, output, "utf8");
  console.log(outputPath);
}
