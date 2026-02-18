.PHONY: help install test clean migrate run docker-up docker-down

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements.txt

test: ## Run all tests
	pytest tests/ -v --tb=short

test-phase0: ## Run Phase 0 requirement tests
	pytest tests/test_phase0_requirements.py -v -m phase0

test-api: ## Run API endpoint tests
	pytest tests/test_api_endpoints.py -v -m integration

test-coverage: ## Run tests with coverage report
	pytest --cov=. --cov-report=html --cov-report=term

clean: ## Clean up temporary files
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .coverage

migrate: ## Run database migrations
	python manage.py makemigrations
	python manage.py migrate

migrate-reset: ## Reset database (WARNING: Deletes all data)
	python manage.py flush --no-input
	python manage.py migrate

run: ## Run development server
	python manage.py runserver

shell: ## Open Django shell
	python manage.py shell

superuser: ## Create superuser
	python manage.py createsuperuser

sample-data: ## Create sample data for testing
	python manage.py create_sample_data

docker-up: ## Start Docker services (db, redis)
	docker compose up -d db redis

docker-down: ## Stop Docker services
	docker compose down

docker-logs: ## View Docker logs
	docker compose logs -f

collectstatic: ## Collect static files
	python manage.py collectstatic --no-input

check: ## Run Django system check
	python manage.py check

lint: ## Run code linters (if installed)
	@echo "Running flake8..."
	@flake8 . --exclude=venv,migrations,staticfiles || echo "flake8 not installed"
	@echo "Running pylint..."
	@pylint accounts devices messages api frontend --errors-only || echo "pylint not installed"

format: ## Format code with black (if installed)
	@black . --exclude="venv|migrations|staticfiles" || echo "black not installed"

verify: ## Verify system and requirements
	python scripts/verify_system.py
	pytest tests/test_requirements.py -v

all: clean install migrate test ## Clean, install, migrate, and test

