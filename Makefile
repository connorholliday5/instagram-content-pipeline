.PHONY: help build up down logs shell py alembic revision upgrade downgrade

help:
@echo "Targets:"
@echo "  make build      - Build docker images"
@echo "  make up         - Start services (db + app)"
@echo "  make down       - Stop services"
@echo "  make logs       - Tail app logs"
@echo "  make shell      - Open shell in app container"
@echo "  make py ARGS=.. - Run python inside app container"
@echo "  make alembic ARGS=..   - Run alembic inside app container"
@echo "  make revision MSG=...  - Create a migration revision"
@echo "  make upgrade           - Apply migrations (head)"
@echo "  make downgrade         - Downgrade one migration"

build:
docker compose build

up:
docker compose up -d

down:
docker compose down

logs:
docker compose logs -f --tail=200 app

shell:
docker compose exec app sh

py:
docker compose run --rm app python $(ARGS)

alembic:
docker compose run --rm app alembic $(ARGS)

revision:
docker compose run --rm app alembic revision -m "$(MSG)"

upgrade:
docker compose run --rm app alembic upgrade head

downgrade:
docker compose run --rm app alembic downgrade -1
