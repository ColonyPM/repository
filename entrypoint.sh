#!/bin/sh
set -e

# Wait for Postgres if configured
if [ -n "$POSTGRES_HOST" ]; then
  POSTGRES_PORT=${POSTGRES_PORT:-5432}
  echo "Waiting for Postgres at $POSTGRES_HOST:$POSTGRES_PORT..."
  until nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
    sleep 0.5
  done
  echo "Postgres is up!"
fi

# Run migrations if enabled
if [ "$RUN_MIGRATIONS" = "1" ]; then
  echo "Running migrations..."
  python manage.py migrate --noinput
fi

# Collect static files if enabled (prod)
if [ "$DJANGO_COLLECTSTATIC" = "1" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

echo "Starting app: $*"
exec "$@"
