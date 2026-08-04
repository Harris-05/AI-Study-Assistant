#!/bin/sh
# Runs on every container start on the Oracle Cloud instance. Unlike Render
# (which has a dashboard "pre-deploy command" field), a plain `docker run`/
# docker-compose setup has nothing that runs migrations for you -- so do it
# here, before gunicorn starts serving traffic.
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting gunicorn..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:"${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-1800}"