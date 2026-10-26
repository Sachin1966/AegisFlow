.PHONY: help install db-migrate db-seed generate-entities generate-tx stream-tx test docker-up docker-down clean

PYTHON ?= python

help:
	@echo "AegisFlow Command Line Interface Utility"
	@echo "----------------------------------------"
	@echo "make install           Install dependencies for txgen, ml, services"
	@echo "make db-migrate        Run Alembic database migrations"
	@echo "make db-seed           Seed initial data (users, sanctions, accounts)"
	@echo "make generate-entities Generate population of accounts, devices, IPs, merchants"
	@echo "make generate-tx       Generate batch synthetic transactions with fraud rings & typologies"
	@echo "make test              Run unit and integration test suite"
	@echo "make docker-up         Start Docker Compose containers"
	@echo "make docker-down       Stop Docker Compose containers"

install:
	pip install -e ./generator
	pip install -e ./ml
	pip install -r requirements.txt || true

db-migrate:
	alembic -c db/alembic.ini upgrade head

db-seed:
	$(PYTHON) db/seed/seed.py

generate-entities:
	$(PYTHON) -m txgen.main seed-entities --num-accounts 1000 --num-devices 500 --num-ips 400 --num-merchants 200

generate-tx:
	$(PYTHON) -m txgen.main generate-batch --count 50000 --fraud-ratio 0.05

stream-tx:
	$(PYTHON) -m txgen.main stream --rate 10

test:
	pytest tests/unit tests/integration -v

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
