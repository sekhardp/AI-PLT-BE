set shell := ["bash", "-cu"]

default:
    @just --list

install:
    uv sync

run:
    uv run python -m app.main

serve:
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

lint:
    uv run python -m compileall app

clean:
    find . -type d -name "__pycache__" -prune -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete

test:
    PYTHONPATH=. uv run pytest -v

migrate:
    uv run alembic upgrade head

rollback:
    uv run alembic downgrade -1

reset-db:
    PYTHONPATH=. uv run python scripts/reset_db.py
