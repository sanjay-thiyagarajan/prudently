.PHONY: dev lint test eval seed-registry seed-policy demo-reset verify-deploys

dev:
	uv run uvicorn app:app --reload --port 8000

lint:
	uv run black --check .
	uv run pylint agents routes services

test:
	uv run pytest --cov --cov-fail-under=80

eval:
	uv run python -m evals.run $(ARGS)

seed-registry:
	uv run python -m scripts.seed_registry

seed-policy:
	uv run python -m scripts.seed_policy

demo-reset: ## clear last take's artefacts so a replay fires triggers again
	uv run python -m scripts.demo_reset $(ARGS)

verify-deploys: ## confirm every Reasoning Engine actually works (adk deploy exits 0 on failure)
	uv run python -m scripts.verify_deploys $(ARGS)
