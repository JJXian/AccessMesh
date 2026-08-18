.PHONY: bootstrap up down logs test lint format policy-test eval migrate seed

bootstrap:
	cp .env.example .env
	cd apps/web && npm install

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api web opa postgres

test:
	pytest

lint:
	ruff check apps/api/src apps/api/tests
	mypy apps/api/src
	cd apps/web && npm run lint

format:
	ruff format apps/api/src apps/api/tests
	ruff check --fix apps/api/src apps/api/tests

policy-test:
	docker compose run --rm opa test /policies -v

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m accessmesh.db.seed

eval:
	python -m accessmesh.evals.run
