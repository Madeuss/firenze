COMPOSE := docker compose -f infra/compose/docker-compose.yml
API     := apps/api

.DEFAULT_GOAL := help
.PHONY: help dev down logs psql install api case ask openapi lint fmt typecheck test check migrate evals

help: ## lista os alvos
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/' | expand -t 14

dev: ## sobe o compose local (Postgres+pgvector, Redis, API)
	$(COMPOSE) up -d --build
	@echo "API em http://localhost:8000/docs  ·  Postgres em localhost:5433"

down: ## derruba o compose (mantém o volume de dados)
	$(COMPOSE) down

logs: ## segue os logs do compose
	$(COMPOSE) logs -f

psql: ## abre psql no banco local
	$(COMPOSE) exec db psql -U firenze -d firenze

install: ## sincroniza o venv de apps/api a partir do uv.lock
	cd $(API) && uv sync --extra dev

api: ## roda a API local com reload (sem container)
	cd $(API) && uv run uvicorn firenze.main:app --reload --port 8000

case: ## gera um caso (make case SEED=42 [LOCALE=en] [REVEAL=1] [VENEER=1])
	cd $(API) && uv run firenze generate --seed $(or $(SEED),1) --locale $(or $(LOCALE),pt-BR) $(if $(REVEAL),--reveal,) $(if $(VENEER),--veneer,)

ask: ## pergunta a um suspeito (make ask SEED=42 WHO=sus-1 Q="onde voce estava?")
	cd $(API) && uv run firenze ask --seed $(or $(SEED),1) --suspect $(or $(WHO),sus-1) --question "$(Q)" --locale $(or $(LOCALE),pt-BR)

openapi: ## regenera apps/api/openapi.json
	cd $(API) && uv run python scripts/dump_openapi.py

lint: ## ruff check + format check
	cd $(API) && uv run ruff check .
	cd $(API) && uv run ruff format --check .

fmt: ## formata e aplica correções automáticas
	cd $(API) && uv run ruff check --fix .
	cd $(API) && uv run ruff format .

typecheck: ## mypy
	cd $(API) && uv run mypy src

test: ## pytest
	cd $(API) && uv run pytest

check: lint typecheck test ## tudo que o CI cobra

migrate: ## aplica as migrations (alembic) — fase 1
	@echo "Ainda não existe schema. Chega junto com o gerador de casos (fase 1)." && exit 1

evals: ## roda a suíte de avaliação — fase 3
	@echo "Suíte de evals chega na fase 3. Ver docs/06-plano-de-evals.md." && exit 1
