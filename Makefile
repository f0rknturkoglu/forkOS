# Podman ve Docker ikisiyle de çalışır
CO ?= podman compose
# Gelistirme runtime'i: gunluk runtime + Vite/HMR/--reload/source mount.
DEV = $(CO) -f compose.yaml -f compose.dev.yaml
# Obsidian hibrit runtime'i: host Vault dizinini api container'ina baglar.
OBS = $(CO) -f compose.yaml -f compose.obsidian.yaml
OBS_DEV = $(CO) -f compose.yaml -f compose.obsidian.yaml -f compose.dev.yaml

# Gunluk (stable) runtime — Vite, HMR ve uvicorn --reload YOK.
up:        ; $(CO) up -d
# Gelistirme runtime'i — Vite + HMR + polling + uvicorn --reload.
up-dev:    ; $(DEV) up -d
up-auto:   ; WORKER_ENABLED=1 $(CO) --profile auto up -d
up-auto-dev: ; WORKER_ENABLED=1 $(DEV) --profile auto up -d
# Obsidian Vault baglantili runtime'lar.
up-obsidian:       ; $(OBS) up -d
up-obsidian-dev:   ; $(OBS_DEV) up -d
up-auto-obsidian:  ; WORKER_ENABLED=1 $(OBS) --profile auto up -d
up-auto-obsidian-dev: ; WORKER_ENABLED=1 $(OBS_DEV) --profile auto up -d
worker-up: ; WORKER_ENABLED=1 $(CO) --profile auto up -d worker
worker-down: ; $(CO) stop worker
down:      ; $(CO) down
logs:      ; $(CO) logs -f api web
ps:        ; $(CO) ps
build:     ; $(CO) build
config:    ; $(CO) config --quiet && echo "compose.yaml: OK"
config-dev: ; $(DEV) config --quiet && echo "compose.yaml + compose.dev.yaml: OK"
config-obsidian: ; $(OBS) config --quiet && echo "compose.yaml + compose.obsidian.yaml: OK"
config-obsidian-dev: ; $(OBS_DEV) config --quiet && echo "compose.yaml + compose.obsidian.yaml + compose.dev.yaml: OK"
doctor:     ; ./scripts/forkos_doctor.sh "$(CO)"
sh:        ; $(CO) exec api bash
psql:      ; $(CO) exec db psql -U lifeos -d lifeos
migrate:   ; $(CO) exec api alembic upgrade head
cli:       ; cd backend && .venv/bin/python -m app.cli $(ARGS)
career-ops-setup: ; ./scripts/setup_career_ops.sh
career-ops-browser-setup: ; cd .vendor/career-ops && npx playwright install chromium
TEST_PROJECT ?= forkos-test
test:
	@status=0; \
	$(CO) -p $(TEST_PROJECT) -f compose.yaml -f compose.test.yaml \
		up --build --abort-on-container-exit --exit-code-from backend-test backend-test || status=$$?; \
	$(CO) -p $(TEST_PROJECT) -f compose.yaml -f compose.test.yaml down -v; \
	exit $$status
backup:    ; mkdir -p backend/backups && $(CO) exec -T db sh -c 'pg_dump -U "$${POSTGRES_USER:-lifeos}" -d "$${POSTGRES_DB:-lifeos}" -Fc > /tmp/forkos.dump' && $(CO) cp db:/tmp/forkos.dump ./backend/backups/forkos.dump
  reset:
	$(CO) down -v
	$(CO) up -d
	@i=0; until $(CO) exec -T db sh -c 'pg_isready -U "$${POSTGRES_USER:-lifeos}" -d "$${POSTGRES_DB:-lifeos}"' >/dev/null 2>&1; do \
		i=$$((i+1)); \
		if [ $$i -ge 60 ]; then echo "HATA: db healthcheck zamani asildi (60s)" >&2; exit 1; fi; \
		sleep 1; \
	done
	$(MAKE) migrate

# GERCEK FELAKET KURTARMASI -- tum veritabanini degistirir (Faz 16/28).
# Normal /backup/restore merge eder; bu hedef yalnizca tam geri donus icindir.
# Kullanim: make disaster-restore FILE=backups/forkos-YYYY-MM-DD.json.gz CONFIRM=DISASTER-RESTORE
# - FILE somut bir yol olmali (glob yasak); CONFIRM zorunlu onay degeri.
# - API ve worker yazmalari durdurulur.
# - Safety dump DB konteynerinde pg_dump ile alinir (API imajinda pg_dump yok;
#   `make backup` ayni deseni kullanir). Dump alinamazsa islem DURUR.
# - CLI: migration'lari head'e ceker, tek transaction icinde temizle+yukle+
#   dogrula, yalnizca basariliysa commit eder. Hata -> rollback + dump yolu.
disaster-restore:
	@test -n "$(FILE)" || (echo "HATA: FILE=<mutlak yol> gerekli" && exit 1)
	@test "$(CONFIRM)" = "DISASTER-RESTORE" || (echo "HATA: CONFIRM=DISASTER-RESTORE gerekli" && exit 1)
	@$(CO) stop api worker
	@TS=$$(date +%Y%m%dT%H%M%SZ); DUMP="backend/backups/pre-disaster-$$TS.dump"; \
	mkdir -p backend/backups; \
	if ! $(CO) exec -T db sh -c 'pg_dump -U "$${POSTGRES_USER:-lifeos}" -d "$${POSTGRES_DB:-lifeos}" -Fc' > "$$DUMP"; then \
		rm -f "$$DUMP"; echo "SAFETY DUMP BASARISIZ -- truncate/import baslamaz"; $(CO) start api worker; exit 1; \
	fi; \
	if ! $(CO) exec -T db sh -c 'tmp=/tmp/pre-disaster-validate.dump; cat > "$$tmp"; pg_restore --list "$$tmp" >/dev/null; status=$$?; rm -f "$$tmp"; exit $$status' < "$$DUMP"; then \
		rm -f "$$DUMP"; echo "SAFETY DUMP GECERSIZ -- truncate/import baslamaz"; $(CO) start api worker; exit 1; \
	fi; \
	echo "Safety dump: $$DUMP"; \
	if ! $(CO) run --rm --no-deps api python scripts/disaster_restore.py --file "$(FILE)" --safety-dump "/app/backups/pre-disaster-$$TS.dump" --confirm "$(CONFIRM)"; then \
		echo "RESTORE BASARISIZ -- safety dump: $$DUMP"; $(CO) start api worker; exit 1; \
	fi
	@$(CO) start api worker
	@echo "Disaster restore tamamlandi."

backend-lint:
	$(CO) -p $(TEST_PROJECT) -f compose.yaml -f compose.test.yaml \
		run --rm --no-deps backend-test ruff check app tests scripts

frontend-verify:
	cd frontend && npm ci && npm audit --audit-level=moderate && npm run api:check && npm test && npm run format:check && node scripts/check-endpoint-coverage.mjs && node scripts/check-dead-exports.mjs && npm run build

extension-verify:
	cd extension && npm ci && npm test

verify: test backend-lint frontend-verify extension-verify
