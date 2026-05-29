#!/bin/sh
set -e

mkdir -p "${UPLOAD_ORIGINAL_FOLDER:-/app/uploads/original}"
mkdir -p "${UPLOAD_PROCESSED_FOLDER:-/tmp/medextract-processed}"
mkdir -p /app/data
mkdir -p "${PADDLE_PDX_CACHE_HOME:-/app/.paddlex-cache}"

ENABLE_BACKGROUND_WORKER=false flask --app run.py init-db

case "$1" in
  web)
    exec gunicorn \
      --bind "0.0.0.0:${PORT:-5000}" \
      --workers "${WEB_CONCURRENCY:-1}" \
      --threads "${WEB_THREADS:-4}" \
      --timeout "${WEB_TIMEOUT:-240}" \
      --access-logfile - \
      --error-logfile - \
      run:app
    ;;
  worker)
    exec python worker.py
    ;;
  *)
    exec "$@"
    ;;
esac
