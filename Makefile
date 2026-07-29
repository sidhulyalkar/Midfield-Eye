.PHONY: install test lint demo demo-v2 verify clean

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
