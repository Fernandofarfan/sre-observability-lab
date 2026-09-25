.PHONY: up down logs logs-all test lint format typecheck traffic chaos-latency chaos-errors chaos-gradual chaos-full clean status

up:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f api

logs-all:
	docker compose logs -f

test:
	pytest tests/ -v --tb=short

lint:
	ruff check app/ tests/ scripts/

format:
	ruff format app/ tests/ scripts/

typecheck:
	mypy app/ --ignore-missing-imports

traffic:
	python scripts/traffic_generator.py --duration 300

chaos-latency:
	python scripts/chaos_injection.py --scenario latency-spike

chaos-errors:
	python scripts/chaos_injection.py --scenario error-storm

chaos-gradual:
	python scripts/chaos_injection.py --scenario gradual-degradation

chaos-full:
	python scripts/chaos_injection.py --scenario full-chaos

clean:
	docker compose down -v --rmi local

status:
	docker compose ps
