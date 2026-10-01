#!/usr/bin/env bash
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_TEXT="${1:-docker compose}"
read -r -a COMPOSE <<<"${COMPOSE_TEXT}"
cd "${REPO_ROOT}"

passed=0
failed=0
warned=0

pass() { printf 'OK    %s\n' "$1"; passed=$((passed + 1)); }
fail() { printf 'FAIL  %s\n' "$1"; failed=$((failed + 1)); }
warn() { printf 'WARN  %s\n' "$1"; warned=$((warned + 1)); }

http_ok() {
  local name="$1" url="$2"
  if curl --fail --silent --show-error --max-time 10 "${url}" >/dev/null; then
    pass "${name}"
  else
    fail "${name} (${url})"
  fi
}

printf 'forkOS doctor\n\n'

if command -v docker >/dev/null 2>&1 && [ "$(docker context show 2>/dev/null)" = "orbstack" ]; then
  pass "Container motoru: OrbStack"
else
  warn "Aktif Docker context OrbStack değil"
fi

for service in db api web; do
  container_id="$(${COMPOSE[@]} ps -q "${service}" 2>/dev/null)"
  if [ -z "${container_id}" ]; then
    fail "${service} container bulunamadı"
    continue
  fi
  state="$(docker inspect --format '{{.State.Status}}' "${container_id}" 2>/dev/null)"
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${container_id}" 2>/dev/null)"
  if [ "${state}" = "running" ] && { [ "${health}" = "healthy" ] || [ "${health}" = "none" ]; }; then
    pass "${service} container (${health})"
  else
    fail "${service} container (state=${state:-unknown}, health=${health:-unknown})"
  fi
done

http_ok "Web arayüzü" "http://127.0.0.1:5173/"
http_ok "API health" "http://127.0.0.1:8787/health"

heads="$(${COMPOSE[@]} exec -T api alembic heads 2>/dev/null | sed -n 's/ .*//p' | sort)"
current="$(${COMPOSE[@]} exec -T db psql -U lifeos -d lifeos -tAc 'select version_num from alembic_version' 2>/dev/null | tr -d '[:space:]')"
if [ -n "${current}" ] && [ "${current}" = "${heads}" ]; then
  pass "Veritabanı migration head: ${current}"
else
  fail "Migration uyuşmazlığı (db=${current:-yok}, head=${heads:-yok})"
fi

vault_json="$(curl --fail --silent --max-time 10 http://127.0.0.1:8787/api/obsidian/status 2>/dev/null)"
if VAULT_JSON="${vault_json}" python3 -c 'import json,os,sys; d=json.loads(os.environ["VAULT_JSON"]); sys.exit(0 if d.get("available") and d.get("readable") and d.get("writable") and not d.get("conflicts") and not d.get("invalid_files") else 1)' 2>/dev/null; then
  pass "Obsidian Vault okunabilir/yazılabilir"
else
  fail "Obsidian Vault sağlık kontrolü"
fi

career_json="$(curl --fail --silent --max-time 120 http://127.0.0.1:8787/api/system/career-ops/doctor 2>/dev/null)"
career_status="$(CAREER_JSON="${career_json}" python3 -c 'import json,os; print(json.loads(os.environ["CAREER_JSON"]).get("status", "unknown"))' 2>/dev/null)"
if [ "${career_status}" = "ready" ] || [ "${career_status}" = "READY" ]; then
  pass "Career Ops doctor: ${career_status}"
else
  warn "Career Ops doctor: ${career_status:-erişilemedi}"
fi

if command -v hermes >/dev/null 2>&1; then
  if hermes mcp test forkos-brain >/dev/null 2>&1; then
    pass "Hermes → forkOS MCP bağlantısı"
  else
    fail "Hermes → forkOS MCP bağlantısı"
  fi

  model="$(hermes config get model.default 2>/dev/null)"
  provider="$(hermes config get model.provider 2>/dev/null)"
  model_file="${HOME}/.hermes/models/${model}.gguf"
  if [ "${provider}" = "llamacpp" ] && [ -s "${model_file}" ]; then
    pass "Hermes yerel model: ${model}"
  else
    warn "Hermes yerel model doğrulanamadı (provider=${provider:-yok}, model=${model:-yok})"
  fi
else
  warn "Hermes CLI bulunamadı"
fi

printf '\nSonuç: %d OK, %d WARN, %d FAIL\n' "${passed}" "${warned}" "${failed}"
if [ "${failed}" -ne 0 ]; then
  exit 1
fi
