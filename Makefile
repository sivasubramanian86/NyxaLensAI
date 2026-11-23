.PHONY: bootstrap lint test seed-patterns seed-local deploy destroy run-local clean

# ── Python virtualenv root ──────────────────────────────────────────────────
VENV        := .venv
PYTHON      := $(VENV)/Scripts/python
PIP         := $(VENV)/Scripts/pip
PYTEST      := $(VENV)/Scripts/pytest
RUFF        := $(VENV)/Scripts/ruff

bootstrap:
	python -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install \
		"aws-cdk-lib>=2.100.0" \
		"constructs>=10.0.0" \
		"pydantic>=2.0" \
		"boto3>=1.39.8" \
		"requests>=2.31" \
		"httpx>=0.27" \
		"numpy>=1.26" \
		"opensearch-py>=2.4" \
		"requests-aws4auth>=1.2" \
		"aws-xray-sdk>=2.14" \
		"jellyfish>=1.0" \
		"metaphone>=0.6" \
		"pytest>=8.0" \
		"pytest-asyncio>=0.23" \
		"pytest-mock>=3.14" \
		"ruff==0.15.12"
	cd frontend && npm install
	@echo "Bootstrap complete."

lint:
	$(RUFF) check lambdas/ data/ tests/

test:
	$(PYTEST) tests/unit/ -v --tb=short
	@echo "Unit tests passed."

test-integration:
	$(PYTEST) tests/integration/ -v --tb=short

# Seed patterns into Amazon OpenSearch Serverless (requires deployed AOSS collection)
seed-patterns:
	$(PYTHON) data/seed_opensearch.py --mode aoss

# Pre-compute local numpy embeddings (zero-cost fallback after cdk destroy)
seed-local:
	$(PYTHON) data/seed_opensearch.py --mode local
	@echo "Local embeddings written to data/patterns_20_embedded.json"

deploy:
	cd cdk && cdk deploy --require-approval never

destroy:
	cd cdk && cdk destroy --force
	@echo "Stack destroyed. Run 'make seed-local' first if you want the app to keep running."

run-local:
	@echo "Start the Next.js dev server:"
	@echo "  cd frontend && npm run dev"
	@echo "Then set NEXT_PUBLIC_API_URL to your deployed API Gateway URL."

clean:
	rm -rf $(VENV) cdk/cdk.out frontend/.next frontend/node_modules __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
