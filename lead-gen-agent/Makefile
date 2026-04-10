.PHONY: install dev test test-cov demo serve \
        ui ui-build ui-dev \
        docker-build docker-up docker-down docker-logs docker-shell \
        clean lint

# ── Python install ────────────────────────────────────────────────────────────

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov=api --cov-report=term-missing --cov-report=html

# ── Frontend ──────────────────────────────────────────────────────────────────

# Install frontend deps
ui:
	cd frontend && npm install

# Build frontend for production (outputs to frontend/dist)
ui-build:
	cd frontend && npm run build

# Run frontend dev server (hot reload at http://localhost:5173, proxies API to :3000)
ui-dev:
	cd frontend && npm run dev

# ── Running ───────────────────────────────────────────────────────────────────

# Run API only (no frontend build needed — use ui-dev in another terminal)
serve:
	agent serve --host 0.0.0.0 --port 3000 --reload

# Build frontend then start API (serves dashboard at http://localhost:3000)
serve-full: ui-build
	agent serve --host 0.0.0.0 --port 3000

demo:
	python demo/run_demo.py

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build:
	docker build -t ai-lead-gen-agent:latest .

docker-up:
	docker-compose up -d
	@echo ""
	@echo "  Dashboard → http://localhost:$$(grep API_PORT .env 2>/dev/null | cut -d= -f2 || echo 3000)"
	@echo "  API Docs  → http://localhost:$$(grep API_PORT .env 2>/dev/null | cut -d= -f2 || echo 3000)/docs"
	@echo ""

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
	rm -rf frontend/dist frontend/node_modules
