.PHONY: help build up down logs

help:
@echo "Targets:"
@echo "  make build  - Build docker images"
@echo "  make up     - Start services"
@echo "  make down   - Stop services"
@echo "  make logs   - Tail app logs"

build:
docker compose build

up:
docker compose up -d

down:
docker compose down

logs:
docker compose logs -f --tail=200 app
