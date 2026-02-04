# Comic Data Lab

A reproducible data pipeline + analytics lab for comic release metadata:
- Ingest weekly releases (source adapters)
- Normalize + store in a canonical schema (Postgres via Docker)
- Analyze trends (NLP, time series, networks)
- Publish weekly insights (Instagram Graph API + **our own generated visuals**)

## Repo Layout
- `src/cdl/` core library
- `var/cache/` cached raw responses (local only)
- `var/outputs/` generated artifacts (charts/json/images)
- `docs/` roadmap + architecture + data ethics

## Roadmap
See: `docs/roadmap/ROADMAP.md`

## Principles
- Docker-first for reproducibility
- Deterministic artifact runs (manifests + versioning)
- Respect ToS, cache + rate-limit, avoid redistributing copyrighted content
