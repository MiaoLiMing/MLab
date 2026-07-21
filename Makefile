.PHONY: install dev-api dev-web test lint build migrate up down logs

install:
	python -m pip install -e "./backend[dev]"
	pnpm --dir frontend install

dev-api:
	python -m uvicorn app.main:app --app-dir backend --reload

dev-web:
	pnpm --dir frontend dev

test:
	python -m pytest backend/tests
	pnpm --dir frontend test

lint:
	python -m ruff format --check backend/app backend/tests backend/alembic/versions
	python -m ruff check backend/app backend/tests backend/alembic/versions
	pnpm --dir frontend lint

build:
	pnpm --dir frontend build

migrate:
	cd backend && alembic upgrade head

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api worker web

