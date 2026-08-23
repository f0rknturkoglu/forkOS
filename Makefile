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

backend-lint:
	$(CO) -p $(TEST_PROJECT) -f compose.yaml -f compose.test.yaml \
		run --rm --no-deps backend-test ruff check app tests scripts

frontend-verify:
	cd frontend && npm ci && npm audit --audit-level=moderate && npm run api:check && npm test && npm run build

extension-verify:
	cd extension && npm ci && npm test

verify: test backend-lint frontend-verify extension-verify
