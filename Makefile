.PHONY: install test lint demo demo-v2 verify clean showcase showcase-serve frontend-contract frontend-install frontend-dev frontend-verify

install:
	python -m pip install -e ".[all]"

test:
	pytest

lint:
	ruff check --select F src tests scripts examples

demo:
	midfielders-eye demo --output-dir artifacts/demo

demo-v2:
	midfielders-eye demo-v2 --output-dir artifacts/demo-v2

verify: test demo demo-v2

clean:
	rm -rf artifacts .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

showcase:
	midfielders-eye showcase-build --output-dir artifacts/showcase

showcase-serve:
	midfielders-eye showcase-serve --bundle-dir artifacts/showcase

frontend-contract:
	midfielders-eye frontend-contract --output frontend_contract/openapi.json

frontend-install:
	cd frontend && npm install

frontend-dev: showcase
	cd frontend && npm run dev

frontend-verify: showcase
	cd frontend && npm run format:check
	cd frontend && npm run typecheck
	cd frontend && npm run lint
	cd frontend && npm test
	cd frontend && npm run build
	cd frontend && npm run test:e2e
