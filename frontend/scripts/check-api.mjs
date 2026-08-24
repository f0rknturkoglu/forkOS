import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { delimiter } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const backendRoot = resolve(frontendRoot, "../backend");
const localPython = resolve(backendRoot, ".venv/bin/python");
const python = process.env.PYTHON || (existsSync(localPython) ? localPython : "python3");
const pythonPath = process.env.PYTHONPATH
  ? `${backendRoot}${delimiter}${process.env.PYTHONPATH}`
  : backendRoot;

for (const command of [
  [python, ["scripts/export_openapi.py", "--check"], backendRoot],
  [process.execPath, ["scripts/generate-api.mjs", "--check"], frontendRoot],
]) {
  const result = spawnSync(command[0], command[1], {
    cwd: command[2],
    env: { ...process.env, PYTHONPATH: pythonPath },
    stdio: "inherit",
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
