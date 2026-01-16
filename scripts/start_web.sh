#!/usr/bin/env bash
set -e

echo "Running migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
