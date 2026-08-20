.PHONY: dev api-dev web-dev seed probe tf-plan tf-apply deploy lint test eval commit

dev: ## run api + web together
	$(MAKE) -j2 api-dev web-dev

api-dev: ## run FastAPI/ADK backend
	$(MAKE) -C apps/api dev

web-dev: ## run Next.js dashboard
	cd apps/web && npm run dev

seed: ## regenerate synthetic data and load into Firestore/emulator
	uv run --project packages/datagen python -m datagen.seed

probe: ## Day-1 capability verification spike
	bash infra/scripts/day1_capability_probe.sh

tf-plan:
	cd infra/terraform/envs/dev && terraform init -upgrade && terraform plan

tf-apply:
	cd infra/terraform/envs/dev && terraform init && terraform apply

deploy: ## deploy both Cloud Run services
	bash infra/scripts/deploy.sh

lint:
	$(MAKE) -C apps/api lint
	cd apps/web && npm run lint

test:
	$(MAKE) -C apps/api test

eval:
	$(MAKE) -C apps/api eval

commit: lint test ## lint + test staged changes, then commit
	git commit
