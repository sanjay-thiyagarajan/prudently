.PHONY: dev lint test eval

dev:
	uv run uvicorn app:app --reload --port 8000

lint:
	uv run black --check .
	uv run pylint agents routes services

test:
	uv run pytest --cov --cov-fail-under=80

eval:
	uv run python -m evals.run
