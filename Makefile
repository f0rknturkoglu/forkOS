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
test:      ; $(CO) exec api pytest -q
reset:     ; $(CO) down -v && $(CO) up -d && sleep 5 && $(MAKE) migrate
