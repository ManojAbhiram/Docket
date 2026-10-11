# Docket (Python service). Every command lives here. `make help` lists them.
SHELL := /bin/bash
.DEFAULT_GOAL := help
UV ?= uv
STATE := .bearing/state
SKIPPED := $(STATE)/.skipped
# The gates `make check` runs, in order. test-integration needs Postgres, so
# it is a CI job and a manual target, not part of check.
GATES := format-check lint typecheck test vuln
POSTGRES_PORT ?= 5432
MEMORY_OUT ?= .scratch/NOTASK-17/memory.json
MEMORY_COMMAND ?= -m evals.memory_bench --out $(MEMORY_OUT)
SEED_API_URL ?= http://localhost:8080
SEED_STAFF_USERNAME ?= staff.demo
DATABASE_URL ?= postgresql+asyncpg://postgres:postgres@localhost:$(POSTGRES_PORT)/docket
# psql takes the plain URL (no SQLAlchemy driver suffix).
PSQL_URL = $(subst +asyncpg,,$(DATABASE_URL))

# $(call skip,gate,tool): the tool is absent. Print it, record it, and let the
# other gates run; `check` fails on any recorded skip. Never a silent pass.
define skip
{ mkdir -p $(STATE); echo "$(1): SKIPPED ($(2) not installed)"; echo "$(1) $(2)" >> $(SKIPPED); exit 0; }
endef
# $(call need_tool,gate,tool): uv, then the project tool inside the venv.
define need_tool
command -v $(UV) >/dev/null || $(call skip,$(1),uv); $(UV) run --quiet $(2) --version >/dev/null 2>&1 || $(call skip,$(1),$(2))
endef

.PHONY: help setup dev seed-accounts check check-file fix test test-integration lint typecheck format format-check migrate migrate-verify migrate-down migrate-new vuln eval-extract eval-record eval-gate eval-report doctor db db-reset clean
.PHONY: test-memory bench-memory bench-memory-repeat bench-memory-runtime
.PHONY: test-seed-load seed-load

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

setup: ## Install Python 3.14, dependencies (writes uv.lock) and git hooks
	$(UV) python install 3.14
	@if [ -f uv.lock ]; then $(UV) sync --locked --all-groups; else echo "setup: no uv.lock yet, resolving; commit the lockfile it writes"; $(UV) sync --all-groups; fi
	bash .githooks/install.sh
	@echo "setup: the committed .githooks run on commit; .pre-commit-config.yaml is for 'uv run pre-commit run --all-files'"
	@echo "setup done"

dev: ## Run the API locally with reload (reads .env if present)
	@set -a; [ -f .env ] && . ./.env; set +a; $(UV) run uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port "$${PORT:-8080}"

format: ## Format
	$(UV) run ruff format .

format-check: ## Fail if any file is unformatted
	@n=$$(git ls-files -co --exclude-standard '*.py' | wc -l | tr -d ' '); \
	[ "$$n" -gt 0 ] || { echo "format-check: 0 python files, nothing checked" >&2; exit 1; }; \
	$(call need_tool,format-check,ruff); \
	$(UV) run ruff format --check . || { echo "format-check: run make fix" >&2; exit 1; }; \
	echo "format-check: $$n files checked"

lint: ## ruff check
	@n=$$(git ls-files -co --exclude-standard '*.py' | wc -l | tr -d ' '); \
	[ "$$n" -gt 0 ] || { echo "lint: 0 python files, nothing checked" >&2; exit 1; }; \
	$(call need_tool,lint,ruff); \
	$(UV) run ruff check . && echo "lint: $$n files checked"

typecheck: ## mypy strict
	@n=$$(git ls-files -co --exclude-standard 'app/*.py' 'tests/*.py' | wc -l | tr -d ' '); \
	[ "$$n" -gt 0 ] || { echo "typecheck: 0 python files, nothing checked" >&2; exit 1; }; \
	$(call need_tool,typecheck,mypy); \
	$(UV) run mypy app tests && echo "typecheck: $$n files checked"

test: ## Unit tests with coverage (integration tests excluded)
	@n=$$(git ls-files -co --exclude-standard 'tests/test_*.py' 'tests/**/test_*.py' | grep -v '^tests/integration/' | wc -l | tr -d ' '); \
	[ "$$n" -gt 0 ] || { echo "test: 0 test files, nothing checked" >&2; exit 1; }; \
	$(call need_tool,test,pytest); \
	set -o pipefail; $(UV) run pytest -m "not integration" 2>&1 | tail -60 && echo "test: $$n test files checked"

test-integration: ## Repository tests against Postgres (needs make db and make migrate; a CI job, not part of check)
	@n=$$(git ls-files -co --exclude-standard 'tests/integration/test_*.py' | wc -l | tr -d ' '); \
	[ "$$n" -gt 0 ] || { echo "test-integration: 0 test files, nothing checked" >&2; exit 1; }; \
	set -o pipefail; DATABASE_URL=$(DATABASE_URL) $(UV) run pytest -m integration --no-cov tests/integration 2>&1 | tail -60 && echo "test-integration: $$n test files checked"

vuln: ## pip-audit over the locked runtime dependencies
	@command -v $(UV) >/dev/null || $(call skip,vuln,uv); command -v uvx >/dev/null || $(call skip,vuln,uvx); \
	[ -f uv.lock ] || { echo "vuln: no uv.lock; run make setup and commit it" >&2; exit 1; }; \
	n=$$($(UV) export --frozen --no-dev --no-hashes --no-header --no-emit-project | grep -c '==' || true); \
	[ "$$n" -gt 0 ] || { echo "vuln: 0 packages, nothing checked" >&2; exit 1; }; \
	uvx pip-audit --strict --no-deps -r <($(UV) export --frozen --no-dev --no-hashes --no-header --no-emit-project | grep -E '^[A-Za-z0-9]') && echo "vuln: $$n packages checked"

eval-extract: ## Real extraction accuracy on the 30 labelled documents (RapidOCR, local, free)
	$(UV) run python -m evals.extract_bench rapidocr

test-memory: ## Narrow regression checks for OCR recycling and real engine output
	$(UV) run pytest --no-cov tests/test_process_engine.py tests/test_config.py tests/integration/test_rapidocr_engine.py

bench-memory: ## Sample API and OCR child RSS over all labelled pages (Linux, no database calls)
	$(UV) run python $(MEMORY_COMMAND)

bench-memory-repeat: ## Repeat the RSS benchmark in three fresh processes
	@for run in 1 2 3; do $(MAKE) --no-print-directory bench-memory MEMORY_OUT=.scratch/NOTASK-17/memory-repeat-$$run.json || exit $$?; done

bench-memory-runtime: ## Drive an isolated local container with uploads, real OCR and concurrent logins
	$(UV) run python -m evals.memory_runtime

eval-record: ## Record RapidOCR words for the 30 documents (live, local, run by a person)
	$(UV) run python -m evals.recordings rapidocr

eval-gate: ## Replay the recording and compare with evals/ocr/gate.yaml (no live engine)
	@$(UV) run python -m evals.extract_bench recorded --recording evals/recordings/rapidocr.json --out evals/ocr/extraction || exit 1; \
	$(UV) run python -m evals.gate_check evals/ocr/extraction/recorded-all.summary.json; rc=$$?; \
	if [ "$$rc" -eq 2 ] && [ "$(EVAL_ALLOW_NO_BASELINE)" = "1" ]; then echo "eval-gate: no baseline accepted yet, nothing gated (EVAL_ALLOW_NO_BASELINE=1)"; exit 0; fi; \
	exit $$rc

eval-report: ## Write docs/testing/extraction-accuracy.md from the eval summaries
	$(UV) run python -m evals.extraction_report

check: ## The gate: every gate in GATES, then the tally. CI runs exactly this.
	@mkdir -p $(STATE); rm -f $(SKIPPED) $(STATE)/.check-passed
	@for g in $(GATES); do $(MAKE) --no-print-directory $$g || { echo "check: $$g failed" >&2; exit 1; }; done
	@s=$$(cut -d' ' -f1 $(SKIPPED) 2>/dev/null | sort -u | wc -l | tr -d ' '); r=$$(( $(words $(GATES)) - s )); \
	echo "check: $$r gates run, $$s skipped"; \
	if [ "$$s" -eq 0 ]; then touch $(STATE)/.check-passed; echo "check: passed"; \
	elif [ "$${BEARING_ALLOW_SKIP:-0}" = "1" ] && [ -z "$$CI" ]; then sed 's/^/  skipped: /' $(SKIPPED); echo "check: passed with skips (BEARING_ALLOW_SKIP=1 is a local convenience; CI never sets it)"; \
	else sed 's/^/  skipped: /' $(SKIPPED); echo "check: FAILED, $$s gate(s) skipped; run make setup, or BEARING_ALLOW_SKIP=1 make check locally" >&2; exit 1; fi

check-file: ## Lint one edited file, FILE=path (the Bearing edit hook runs this)
	@[ -n "$(FILE)" ] || { echo "check-file: FILE is empty, nothing checked" >&2; exit 1; }; \
	[ -f "$(FILE)" ] || { echo "check-file: $(FILE) does not exist, nothing checked" >&2; exit 1; }; \
	case "$(FILE)" in \
	  *.py) command -v $(UV) >/dev/null || { echo "check-file: uv not installed, $(FILE) not checked"; exit 0; }; $(UV) run ruff check --quiet --force-exclude "$(FILE)" || exit 1;; \
	  *) echo "check-file: no per-file check for $(FILE)"; exit 0;; \
	esac; \
	echo "check-file: 1 file checked"

fix: format ## Apply every automatic fix
	@$(UV) run ruff check --fix . || true

db: ## Start Postgres in Docker (host port POSTGRES_PORT, default 5432)
	POSTGRES_PORT=$(POSTGRES_PORT) docker compose up -d --wait postgres

db-reset: ## Drop and recreate the local database (destructive)
	POSTGRES_PORT=$(POSTGRES_PORT) docker compose down -v && POSTGRES_PORT=$(POSTGRES_PORT) docker compose up -d --wait postgres

migrate: ## alembic upgrade head
	DATABASE_URL=$(DATABASE_URL) $(UV) run alembic upgrade head

seed-accounts: ## Create the two demo accounts and print their one-time passwords once
	DATABASE_URL=$(DATABASE_URL) $(UV) run python -m app.db.seed_accounts

test-seed-load: ## Verify synthetic API loading and idempotent reload against isolated Postgres
	DATABASE_URL=$(DATABASE_URL) $(UV) run pytest --no-cov tests/integration/api/test_seed_load.py

seed-load: ## Load 20 synthetic applications and 30 documents into the local API; prompt for staff password
	$(UV) run python -m seed.load --base-url $(SEED_API_URL) --username $(SEED_STAFF_USERNAME)

migrate-down: ## alembic downgrade one
	DATABASE_URL=$(DATABASE_URL) $(UV) run alembic downgrade -1

migrate-verify: ## Every Down runs and restores the schema: up, snapshot, down, up, snapshot, diff (a CI step; needs psql)
	@command -v psql >/dev/null || { echo "migrate-verify: psql not installed (postgresql-client), nothing checked" >&2; exit 1; }; \
	[ -f scripts/schema-snapshot.sql ] || { echo "migrate-verify: no scripts/schema-snapshot.sql, nothing checked" >&2; exit 1; }; \
	n=$$(ls alembic/versions/*.py 2>/dev/null | wc -l | tr -d ' '); \
	[ "$$n" -gt 0 ] || { echo "migrate-verify: 0 migrations in alembic/versions, nothing checked" >&2; exit 1; }; \
	mkdir -p $(STATE); snap() { psql "$(PSQL_URL)" -XAtq -v ON_ERROR_STOP=1 -f scripts/schema-snapshot.sql > "$(STATE)/schema-$$1.txt"; }; \
	$(MAKE) --no-print-directory migrate >/dev/null && snap up || exit 1; \
	o=$$(wc -l < $(STATE)/schema-up.txt | tr -d ' '); [ "$$o" -gt 0 ] || { echo "migrate-verify: the schema snapshot is empty, nothing compared" >&2; exit 1; }; \
	$(MAKE) --no-print-directory migrate-down >/dev/null && $(MAKE) --no-print-directory migrate >/dev/null && snap newest || exit 1; \
	diff -u $(STATE)/schema-up.txt $(STATE)/schema-newest.txt || { echo "migrate-verify: the newest downgrade does not undo exactly what its upgrade did" >&2; exit 1; }; \
	DATABASE_URL=$(DATABASE_URL) $(UV) run alembic downgrade base >/dev/null && $(MAKE) --no-print-directory migrate >/dev/null && snap all || exit 1; \
	diff -u $(STATE)/schema-up.txt $(STATE)/schema-all.txt || { echo "migrate-verify: running every downgrade and every upgrade again changed the schema" >&2; exit 1; }; \
	echo "migrate-verify: $$n migrations, every downgrade ran, $$o schema objects identical after down and up"

migrate-new: ## Autogenerate the next migration: make migrate-new name=add_invoices
	@[ -n "$(name)" ] || { echo "usage: make migrate-new name=add_invoices" >&2; exit 2; }
	@id=$$(printf '%04d' $$(( $$(ls alembic/versions/*.py 2>/dev/null | wc -l) + 1 ))); \
	DATABASE_URL=$(DATABASE_URL) $(UV) run alembic revision --autogenerate --rev-id "$$id" -m "$(name)" && \
	echo "migrate-new: alembic/versions/$${id}_$(name).py written; read every line before committing"

doctor: ## Environment diagnostics
	@echo "uv:        $$(command -v $(UV) >/dev/null && $(UV) --version || echo missing)"
	@echo "python:    $$($(UV) run python --version 2>/dev/null || echo 'missing (run make setup)')"
	@echo "ruff:      $$($(UV) run --quiet ruff --version 2>/dev/null || echo missing)"
	@echo "mypy:      $$($(UV) run --quiet mypy --version 2>/dev/null || echo missing)"
	@echo "alembic:   $$($(UV) run --quiet alembic --version 2>/dev/null || echo missing)"
	@echo "docker:    $$(command -v docker >/dev/null && docker --version || echo missing)"
	@echo "lock:      $$([ -f uv.lock ] && echo present || echo 'MISSING (run make setup and commit uv.lock)')"
	@echo "hooksPath: $$(git config core.hooksPath || echo 'NOT SET (run make setup)')"

clean: ## Remove caches and build output
	rm -rf .venv .ruff_cache .mypy_cache .pytest_cache .coverage htmlcov dist build $(STATE)/.check-passed $(SKIPPED)
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

# Deployment to one Linux VM over SSH (docs/runbooks/deploy.md). Every deploy-* target runs from
# your laptop. Your settings live in deploy/deploy.local.mk (ignored by git), or pass them as
# `make deploy DEPLOY_HOST=ubuntu@1.2.3.4 ...`. The images are built here and sent to the server,
# so a small server never has to compile anything. No target removes the database volume.
-include deploy/deploy.local.mk
DEPLOY_HOST ?=
DEPLOY_KEY ?=
DEPLOY_DOMAIN ?=
DEPLOY_DIR ?= Docket
DEPLOY_PLATFORM ?= linux/amd64
DEPLOY_REPO ?= $(shell git remote get-url origin 2>/dev/null)
DOCKET_VERSION ?= $(shell git rev-parse --short HEAD 2>/dev/null)
PUBLIC_ORIGIN ?= https://$(DEPLOY_DOMAIN)
WEB_PORT ?= 8081
BACKUP_DIR ?= .scratch/backups
SERVICE ?= api
LINES ?= 100
SSH_OPTS = -i $(DEPLOY_KEY) -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30
SSH = ssh $(SSH_OPTS) $(DEPLOY_HOST)
SSH_TTY = ssh -t $(SSH_OPTS) $(DEPLOY_HOST)
# Run on the server: CD enters the checkout, DC is Compose with the production settings.
CD = cd $(DEPLOY_DIR) &&
DC = docker compose --env-file deploy/production.env -f docker-compose.prod.yml

.PHONY: deploy deploy-first deploy-bootstrap deploy-clone deploy-caddy deploy-build deploy-push deploy-release
.PHONY: deploy-verify deploy-apply deploy-env deploy-status deploy-logs deploy-ssh deploy-seed-accounts
.PHONY: deploy-backup deploy-restore deploy-rollback deploy-prune

# $(call need_deploy,target): a host and a key file are set.
define need_deploy
@[ -n "$(DEPLOY_HOST)" ] || { echo "$(1): set DEPLOY_HOST (for example ubuntu@1.2.3.4) in deploy/deploy.local.mk" >&2; exit 1; }; \
[ -f "$(DEPLOY_KEY)" ] || { echo "$(1): DEPLOY_KEY must be the path of your SSH private key file" >&2; exit 1; }
endef
# $(call need_domain,target): the public domain is set.
define need_domain
@[ -n "$(DEPLOY_DOMAIN)" ] || { echo "$(1): set DEPLOY_DOMAIN (for example docket-demo.duckdns.org)" >&2; exit 1; }
endef

# One-time server preparation. Safe to run again: it moves the 80 and 443 rules above the
# REJECT rule that Oracle images ship with, adds swap and Docker only when they are missing.
define DEPLOY_BOOTSTRAP_SCRIPT
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
for port in 80 443; do
  while sudo iptables -D INPUT -p tcp --dport $$port -j ACCEPT 2>/dev/null; do :; done
  pos=$$(sudo iptables -L INPUT -n --line-numbers | awk '/REJECT/ {print $$1; exit}')
  sudo iptables -I INPUT $${pos:-1} -p tcp --dport $$port -j ACCEPT
done
sudo apt-get update -qq
sudo apt-get install -y -qq iptables-persistent ca-certificates curl git caddy
sudo netfilter-persistent save
if ! swapon --show | grep -q /swapfile; then
  [ -f /swapfile ] || { sudo fallocate -l 2G /swapfile; sudo chmod 600 /swapfile; sudo mkswap /swapfile >/dev/null; }
  sudo swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi
command -v docker >/dev/null || curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$$USER"
echo "bootstrap: done"
endef
export DEPLOY_BOOTSTRAP_SCRIPT

# Clone the repository on the server and write deploy/production.env once, with a random
# database password that is never printed. Running it again keeps the password.
define DEPLOY_CLONE_SCRIPT
set -euo pipefail
[ -d $(DEPLOY_DIR)/.git ] || git clone -q $(DEPLOY_REPO) $(DEPLOY_DIR)
cd $(DEPLOY_DIR)
git checkout -q main
if [ ! -f deploy/production.env ]; then
  cp deploy/production.env.example deploy/production.env
  chmod 600 deploy/production.env
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$$(openssl rand -hex 24)|" deploy/production.env
  echo "clone: wrote deploy/production.env with a new random database password"
else
  echo "clone: deploy/production.env already exists, password kept"
fi
sed -i "s|^PUBLIC_ORIGIN=.*|PUBLIC_ORIGIN=$(PUBLIC_ORIGIN)|" deploy/production.env
sed -i "s|^DOCKET_VERSION=.*|DOCKET_VERSION=$(DOCKET_VERSION)|" deploy/production.env
echo "clone: PUBLIC_ORIGIN and DOCKET_VERSION set"
endef
export DEPLOY_CLONE_SCRIPT

deploy: ## Ship main: build here, send, start on the server, verify (the everyday command)
	$(call need_deploy,deploy)
	$(call need_domain,deploy)
	@[ "$$(git rev-parse --abbrev-ref HEAD)" = main ] || { echo "deploy: check out main first" >&2; exit 1; }
	@git diff --quiet && git diff --cached --quiet || { echo "deploy: commit or stash your changes first" >&2; exit 1; }
	@git fetch -q origin main && [ "$$(git rev-parse HEAD)" = "$$(git rev-parse origin/main)" ] || { echo "deploy: main differs from origin/main, push or pull first" >&2; exit 1; }
	@$(MAKE) deploy-build deploy-push deploy-release deploy-verify

deploy-first: ## First time only: prepare the server, clone, ship, start, set up HTTPS
	$(call need_deploy,deploy-first)
	$(call need_domain,deploy-first)
	@$(MAKE) deploy-bootstrap deploy-clone deploy-build deploy-push deploy-release deploy-caddy deploy-verify
	@echo "deploy-first: now run make deploy-seed-accounts and copy the two passwords it prints once"

deploy-bootstrap: ## Prepare the server: firewall order, swap, Docker, Caddy (safe to repeat)
	$(call need_deploy,deploy-bootstrap)
	@printf '%s\n' "$$DEPLOY_BOOTSTRAP_SCRIPT" | $(SSH) bash -s

deploy-clone: ## Clone the repo on the server and write deploy/production.env (keeps an existing password)
	$(call need_deploy,deploy-clone)
	$(call need_domain,deploy-clone)
	@printf '%s\n' "$$DEPLOY_CLONE_SCRIPT" | $(SSH) bash -s

deploy-caddy: ## Point Caddy at the web container for DEPLOY_DOMAIN (HTTPS certificate is automatic)
	$(call need_deploy,deploy-caddy)
	$(call need_domain,deploy-caddy)
	@printf '%s {\n  reverse_proxy 127.0.0.1:$(WEB_PORT)\n}\n' "$(DEPLOY_DOMAIN)" | $(SSH) 'sudo tee /etc/caddy/Caddyfile >/dev/null && sudo systemctl reload caddy && echo "caddy: reloaded for $(DEPLOY_DOMAIN)"'

deploy-build: ## Build the API and web images here for the server's CPU, tagged with the commit
	docker build --platform $(DEPLOY_PLATFORM) -t docket-api:$(DOCKET_VERSION) .
	docker build --platform $(DEPLOY_PLATFORM) -t docket-web:$(DOCKET_VERSION) ./frontend

deploy-push: ## Send the built images to the server
	$(call need_deploy,deploy-push)
	@set -o pipefail; docker save docket-api:$(DOCKET_VERSION) docket-web:$(DOCKET_VERSION) | gzip | $(SSH) 'gunzip | docker load'

deploy-release: ## On the server: pull main, set the version, start the new containers (migrations run)
	$(call need_deploy,deploy-release)
	@$(SSH) 'cd $(DEPLOY_DIR) && git fetch -q origin main && git checkout -q main && git merge -q --ff-only origin/main && sed -i "s|^DOCKET_VERSION=.*|DOCKET_VERSION=$(DOCKET_VERSION)|" deploy/production.env && $(DC) up -d && $(DC) ps'

deploy-verify: ## Check the containers and the public /healthz (retries while the API starts)
	$(call need_deploy,deploy-verify)
	$(call need_domain,deploy-verify)
	@$(SSH) '$(CD) $(DC) ps'
	@curl -fsS --retry 12 --retry-delay 5 --retry-connrefused --max-time 10 $(PUBLIC_ORIGIN)/healthz && echo " <- $(PUBLIC_ORIGIN)/healthz"

deploy-apply: ## Apply a changed deploy/production.env or compose file without rebuilding
	$(call need_deploy,deploy-apply)
	@$(SSH) '$(CD) $(DC) up -d && $(DC) ps'

deploy-env: ## Edit deploy/production.env on the server (then make deploy-apply)
	$(call need_deploy,deploy-env)
	@$(SSH_TTY) 'cd $(DEPLOY_DIR) && nano deploy/production.env'

deploy-status: ## Containers, memory, disk and the image versions on the server
	$(call need_deploy,deploy-status)
	@$(SSH) '$(CD) $(DC) ps; echo; docker stats --no-stream; echo; free -h; df -h / | tail -1; echo; docker images --format "{{.Repository}}:{{.Tag}} {{.CreatedSince}}" | grep ^docket'

deploy-logs: ## Server logs: make deploy-logs SERVICE=api LINES=200 (api, web, postgres, migrate)
	$(call need_deploy,deploy-logs)
	@$(SSH) '$(CD) $(DC) logs --tail $(LINES) $(SERVICE)'

deploy-ssh: ## Open a shell on the server
	$(call need_deploy,deploy-ssh)
	@$(SSH_TTY)

deploy-seed-accounts: ## Create the two demo accounts; the passwords print once
	$(call need_deploy,deploy-seed-accounts)
	@$(SSH) '$(CD) $(DC) run --rm api python -m app.db.seed_accounts'

deploy-backup: ## Download a compressed database dump into .scratch/backups
	$(call need_deploy,deploy-backup)
	@mkdir -p $(BACKUP_DIR)
	@set -o pipefail; f="$(BACKUP_DIR)/docket-$$(date +%F-%H%M).sql.gz"; $(SSH) '$(CD) $(DC) exec -T postgres pg_dump -U docket docket | gzip' > "$$f" && [ -s "$$f" ] && echo "backup: $$f ($$(du -h "$$f" | cut -f1))" || { rm -f "$$f"; echo "backup: failed" >&2; exit 1; }

deploy-restore: ## Replace the database from a dump: make deploy-restore FILE=x.sql.gz CONFIRM=yes
	$(call need_deploy,deploy-restore)
	@[ -f "$(FILE)" ] || { echo "deploy-restore: FILE=path/to/dump.sql.gz is required" >&2; exit 1; }
	@[ "$(CONFIRM)" = yes ] || { echo "deploy-restore: this replaces every table on the server; add CONFIRM=yes" >&2; exit 1; }
	@$(MAKE) deploy-backup
	@$(SSH) '$(CD) $(DC) stop api'
	@$(SSH) '$(CD) $(DC) exec -T postgres psql -U docket docket -v ON_ERROR_STOP=1 -c "drop schema public cascade; create schema public;"'
	@gunzip -c "$(FILE)" | $(SSH) '$(CD) $(DC) exec -T postgres psql -U docket docket -v ON_ERROR_STOP=1'
	@$(SSH) '$(CD) $(DC) up -d'

deploy-rollback: ## Go back to an earlier image: make deploy-rollback VERSION=<short commit>
	$(call need_deploy,deploy-rollback)
	@[ -n "$(VERSION)" ] || { echo "deploy-rollback: VERSION=<short commit> is required (make deploy-status lists them)" >&2; exit 1; }
	@$(SSH) 'docker image inspect docket-api:$(VERSION) docket-web:$(VERSION) >/dev/null && cd $(DEPLOY_DIR) && sed -i "s|^DOCKET_VERSION=.*|DOCKET_VERSION=$(VERSION)|" deploy/production.env && $(DC) up -d && $(DC) ps'

deploy-prune: ## Remove unused dangling images on the server (tagged versions stay for rollback)
	$(call need_deploy,deploy-prune)
	@$(SSH) 'docker image prune -f && df -h / | tail -1'
