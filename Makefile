PYTHON ?= python

setup:
	cd backend && $(PYTHON) -m venv .venv && .venv/bin/pip install -e '.[dev]'
	cd frontend && npm install

backend:
	cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

worker:
	@echo "Local synchronous job mode is active; production queue adapter is documented in docs/ARCHITECTURE.md"

seed:
	cd backend && PYTHONPATH=. $(PYTHON) -m app.cli reset-seed

test:
	cd backend && PYTHONPATH=. pytest
	cd frontend && npm run test

lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint

typecheck:
	cd backend && mypy app --no-incremental --follow-imports=skip
	cd frontend && npm run typecheck

build:
	cd frontend && npm run build

demo: seed
	@echo "Run 'make backend' and 'make frontend' in separate terminals, then open http://localhost:3000"

clean:
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache frontend/.next
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
