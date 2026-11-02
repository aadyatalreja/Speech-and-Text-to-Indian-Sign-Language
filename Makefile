PYTHON ?= python

.PHONY: test lint dev
test:
	cd backend && $(PYTHON) -m pytest -q
	cd frontend && npm test && npx tsc --noEmit && npm run build

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

dev:
	docker compose -f docker-compose.yml -f dockercompose.dev.yml up --build
