.PHONY: help install dev docker-up docker-down test

help:
	@echo "Available commands:"
	@echo "  install      Install dependencies"
	@echo "  dev          Run development server"
	@echo "  docker-up    Start all services with Docker"
	@echo "  docker-down  Stop all services"
	@echo "  test         Run tests"
	@echo "  init-db      Initialize database"

install:
	pip install -r requirements.txt

dev:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

test:
	pytest tests/

init-db:
	python scripts/init_db.py

worker:
	celery -A backend.tasks.celery_app worker --loglevel=info --concurrency=4

beat:
	celery -A backend.tasks.celery_app beat --loglevel=info
