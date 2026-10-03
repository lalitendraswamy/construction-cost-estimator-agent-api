.PHONY: install dev test test-cov lint format typecheck seed ingest indexes check-db graph up down evals

PY ?= python
# UTF-8 mode: Windows consoles default to cp1252, which can't print ₹ / Telugu / Hindi.
export PYTHONUTF8 := 1

install:            ## install runtime + dev deps
	$(PY) -m pip install -e ".[dev]"
	pre-commit install

dev:                ## run API with autoreload
	uvicorn estimator_agent.main:app --reload --port 8000

test:               ## unit + integration tests (no network)
	pytest

test-cov:
	pytest --cov --cov-report=term-missing

lint:
	ruff check src tests scripts

format:
	ruff format src tests scripts && ruff check --fix src tests scripts

typecheck:
	mypy src

indexes:            ## create Mongo indexes (incl. Atlas vector index)
	$(PY) -m scripts.create_indexes

seed:               ## seed placeholder rate cards
	$(PY) -m scripts.seed_rates

check-db:           ## show which MongoDB is configured and whether it is set up
	$(PY) -m scripts.check_db

ingest:             ## load knowledge-base docs into the vector store
	$(PY) -m scripts.ingest_kb

graph:              ## export the LangGraph diagram (Mermaid) to docs/
	$(PY) -m scripts.export_graph

evals:              ## run LangSmith evaluation dataset (needs real keys)
	$(PY) -m tests.evals.run_evals

up:                 ## run the API in the production Docker image (uses Atlas from .env)
	docker compose up -d --build

down:               ## stop the Docker API
	docker compose down
