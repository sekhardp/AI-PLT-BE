#!/bin/sh
# docker-entrypoint.sh
#
# Runs before uvicorn starts inside the container.

set -e

# Data directory configuration
UPLOAD_DIR="${UPLOAD_DIR:-/app/data/uploads}"
DATA_DIR="${UPLOAD_DIR%/*}"

mkdir -p "$UPLOAD_DIR"
# Ensure the running user owns the data dir if mounted dynamically
chown -R "$(id -u):$(id -g)" "$DATA_DIR" 2>/dev/null || true

# Determine port (Cloud Run sets PORT, fallback to EndpointSettings)
PORT="${PORT:-${ENDPOINT_PORT:-8000}}"

echo "========================================="
echo " AI Platform Backend (AI-PLT-BE)         "
echo "========================================="
echo " Environment : ${APP_ENV:-development}"
echo " Database URL: ${DB_URL:-sqlite:///./app.db}"
echo " Upload dir  : ${UPLOAD_DIR}"
echo " Port        : ${PORT}"
echo "========================================="

# Execute Uvicorn replacing shell process (PID 1) immediately for fast Cloud Run health probe response
exec uvicorn app.main:app \
    --host "${ENDPOINT_HOST:-0.0.0.0}" \
    --port "${PORT}" \
    --log-level "${LOG_LEVEL:-info}" \
    --no-access-log
