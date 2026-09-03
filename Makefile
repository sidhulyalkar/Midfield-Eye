.PHONY: install test lint demo demo-v2 verify clean showcase showcase-serve frontend-contract frontend-install frontend-dev frontend-verify status r1-status r1-sw-validate empirical-build package-demo help

help:
	@echo "Midfielder's Eye — common targets"
	@echo "  make install          Install package + all extras"
	@echo "  make test             Run pytest"
	@echo "  make verify           Tests + synthetic demos"
	@echo "  make showcase         Build Evidence Studio bundle into artifacts/showcase"
	@echo "  make showcase-serve   Serve the FastAPI Evidence Studio"
	@echo "  make frontend-dev     Build showcase then start Vite frontend"
	@echo "  make frontend-verify  Full frontend gate (format, typecheck, lint, test, build, e2e)"
	@echo "  make r1-sw-validate   End-to-end R1 software validation (no empirical claim)"
	@echo "  make empirical-build  Build real-source empirical showcase bundle"
	@echo "  make package-demo     Package static demo for Pages-style hosting"
	@echo "  make status           High-level project / claim-boundary reminder"
	@echo "  make r1-status        Point to R1 pilot runbook and current gate"

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

r1-sw-validate:
	python scripts/run_r1_software_validation.py --output-dir artifacts/r1-sw

empirical-build:
	midfielders-eye empirical-build --output-dir artifacts/showcase/empirical

package-demo: showcase
	cd frontend && npm ci && npm run build
	python scripts/package_static_demo.py --force

status:
	@echo "Midfielder's Eye v0.7"
	@echo "Claim boundary: benchmark contract + software + Decision Microscope ship."
	@echo "Empirical superiority is gated on the real R1 expert-annotated pilot."
	@echo "See README.md, docs/SHOWCASE_AND_DEMO.md, docs/R1_EXECUTION_CHECKLIST.md."
	@echo "Software validation only: make r1-sw-validate"

r1-status:
	@echo "R1 Real Action Menu Pilot"
	@echo "Runbook: docs/R1_REAL_ACTION_MENU_PILOT.md"
	@echo "Checklist: docs/R1_EXECUTION_CHECKLIST.md"
	@echo "Frontend cockpit: /pilot (after showcase-build)"
	@echo "Empty/partial states are intentional — do not invent metrics."
	@echo "Next gates: sample freeze → full double annotation → reliability → provider quality → sequence-held-out benchmark."
	@echo "Software path (no claim): make r1-sw-validate"
