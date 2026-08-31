.PHONY: help install run test docker-up docker-down migrate lint

help:
	@echo "Available commands:"
	@echo "  make install     - Install dependencies into virtualenv"
	@echo "  make run         - Run bot locally"
	@echo "  make test        - Run test suite"
	@echo "  make docker-up   - Start complete Docker Compose stack"
	@echo "  make docker-down - Stop Docker Compose stack"
	@echo "  make migrate     - Run database migrations"
	@echo "  make lint        - Format and lint codebase"

install:
	pip install -r requirements.txt

run:
	python -m src.main

test:
	pytest tests/ -v

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

migrate:
	alembic upgrade head

lint:
	ruff check src/ tests/
