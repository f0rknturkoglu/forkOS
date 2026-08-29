# Podman ve Docker ikisiyle de çalışır
CO ?= podman compose

up:        ; $(CO) up -d
down:      ; $(CO) down
logs:      ; $(CO) logs -f api worker
ps:        ; $(CO) ps
build:     ; $(CO) build
sh:        ; $(CO) exec api bash
psql:      ; $(CO) exec db psql -U lifeos -d lifeos
migrate:   ; $(CO) exec api alembic upgrade head
revision:  ; $(CO) exec api alembic revision --autogenerate -m "$(m)"
TEST_PROJECT ?= forkos-test
test:
	@status=0; \
	$(CO) -p $(TEST_PROJECT) -f compose.yaml -f compose.test.yaml \
		up --build --abort-on-container-exit --exit-code-from backend-test backend-test || status=$$?; \
	$(CO) -p $(TEST_PROJECT) -f compose.yaml -f compose.test.yaml down -v; \
	exit $$status
backup:    ; mkdir -p backend/backups && $(CO) exec -T db sh -c 'pg_dump -U lifeos -d lifeos -Fc > /tmp/forkos.dump' && $(CO) cp db:/tmp/forkos.dump ./backend/backups/forkos.dump
 reset:     ; $(CO) down -v && $(CO) up -d && sleep 5 && $(MAKE) migrate

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
	@TS=$$(date +%Y%m%dT%H%M%SZ); \
	mkdir -p backend/backups; \
	$(CO) exec -T db sh -c 'pg_dump -U "$${POSTGRES_USER:-lifeos}" -d "$${POSTGRES_DB:-lifeos}" -Fc' > backend/backups/pre-disaster-$$TS.dump \
		|| (echo "SAFETY DUMP BASARISIZ -- truncate/import baslamaz" && $(CO) start api worker && exit 1); \
	echo "Safety dump: backend/backups/pre-disaster-$$TS.dump"; \
	$(CO) run --rm --no-deps api python scripts/disaster_restore.py --file "$(FILE)" --safety-dump /app/backups/pre-disaster-$$TS.dump --confirm "$(CONFIRM)" \
		|| (echo "RESTORE BASARISIZ -- safety dump: backend/backups/pre-disaster-$$TS.dump" && $(CO) start api worker && exit 1)
	@$(CO) start api worker
	@echo "Disaster restore tamamlandi."

backend-lint:
	$(CO) -p $(TEST_PROJECT) -f compose.yaml -f compose.test.yaml \
		run --rm --no-deps backend-test ruff check app tests scripts

frontend-verify:
	cd frontend && npm ci && npm audit --audit-level=moderate && npm run api:check && npm test && npm run build

extension-verify:
	cd extension && npm ci && npm test

verify: test backend-lint frontend-verify extension-verify
