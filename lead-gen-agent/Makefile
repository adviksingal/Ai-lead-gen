.PHONY: install dev test test-cov demo serve docker-build docker-up docker-down clean lint

# ── Local development ─────────────────────────────────────────────────────────

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov=api --cov-report=term-missing --cov-report=html

# ── Running ───────────────────────────────────────────────────────────────────

demo:
	python demo/run_demo.py

serve:
	agent serve --host 0.0.0.0 --port 3000 --reload

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build:
	docker build -t ai-lead-gen-agent:latest .

docker-up:
	docker-compose up -d
	@echo "API running at http://localhost:$$(grep API_PORT .env 2>/dev/null | cut -d= -f2 || echo 3000)"
	@echo "Docs at http://localhost:$$(grep API_PORT .env 2>/dev/null | cut -d= -f2 || echo 3000)/docs"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api

docker-shell:
	docker-compose exec api bash

# ── Quality ───────────────────────────────────────────────────────────────────

lint:
	ruff check src/ api/ cli/ --fix

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null; true
	rm -rf dist/ build/ .pytest_cache/ htmlcov/ .coverage
