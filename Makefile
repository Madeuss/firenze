COMPOSE := docker compose -f infra/compose/docker-compose.yml
VENV    := .venv
PY      := $(VENV)/bin/python
ifeq ($(OS),Windows_NT)
PY      := $(VENV)/Scripts/python.exe
endif

.DEFAULT_GOAL := help
.PHONY: help dev down logs psql install api openapi lint fmt typecheck test check migrate evals

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
	$(COMPOSE) exec db psql -U mansao -d mansao

install: ## cria o venv e instala apps/api em modo editável
	python -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e "apps/api[dev]"

api: ## roda a API local com reload (sem container)
	$(PY) -m uvicorn mansao.main:app --reload --port 8000

openapi: ## regenera apps/api/openapi.json
	$(PY) apps/api/scripts/dump_openapi.py

lint: ## ruff check + format check
	$(PY) -m ruff check apps/api
	$(PY) -m ruff format --check apps/api

fmt: ## formata e aplica correções automáticas
	$(PY) -m ruff check --fix apps/api
	$(PY) -m ruff format apps/api

typecheck: ## mypy
	$(PY) -m mypy apps/api/src

test: ## pytest
	$(PY) -m pytest apps/api

check: lint typecheck test ## tudo que o CI cobra

migrate: ## aplica as migrations (alembic) — fase 1
	@echo "Ainda não existe schema. Chega junto com o gerador de casos (fase 1)." && exit 1

evals: ## roda a suíte de avaliação — fase 3
	@echo "Suíte de evals chega na fase 3. Ver docs/06-plano-de-evals.md." && exit 1
