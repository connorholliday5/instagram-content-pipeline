# Roadmap

## Phase 0  Repo scaffolding (this step)
- Repo structure (`src/` layout), docs, `.env.example`, `.gitignore`
- Docker-first scaffolding (Dockerfile + docker-compose)
- Makefile for one-command workflow
- CI (GitHub Actions): lint, test, docker build
- Ethics + data sources doc

## Phase 1  Foundation (research-grade)
- DB schema + migrations (Alembic)
- Run manifests + output bundles: `var/outputs/YYYY-MM-DD/`
- Caching + throttling utilities
- CLI entrypoint (`python -m cdl ...`) runnable in Docker

## Phase 2  Ingestion MVP (1 source)
- One adapter  normalized releases
- Store in Postgres
- Export artifacts (parquet/json)

## Phase 3  Publishing (guaranteed)
- Render our own visuals (cards/charts/carousels)
- Generate captions
- Publish via Instagram Graph API (+ dry-run mode)

## Phase 4  Analytics + Evaluation
- Topic modeling + coherence
- Trend detection + basic backtests
- Network analysis graphs

## Phase 5  Portfolio integration + polish
- Optional FastAPI read-only endpoint for latest outputs
- Mini-paper style docs: methods, limitations, ethics
- CI hardened + tests expanded
