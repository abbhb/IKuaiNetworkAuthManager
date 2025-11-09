#!/bin/bash
set -e

echo "==================================="
echo "Network Manager - Starting Up"
echo "==================================="


# Run database migrations
echo "Running database migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Collect static files (if needed for production)
if [ "${DJANGO_ENV}" = "prod" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
fi


echo "==================================="
echo "Starting services..."
echo "==================================="

# Execute the CMD
exec "$@"
