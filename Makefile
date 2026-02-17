.PHONY: build up down logs restart backup test dev clean

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart

backup:
	./scripts/backup.sh

test:
	python -m pytest tests/ -v

dev:
	FLASK_ENV=development python run.py

clean:
	docker compose down -v --rmi local
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
