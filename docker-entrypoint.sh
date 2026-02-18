#!/bin/bash
set -e

# This entrypoint is ONLY for the web service
# It runs migrations and collectstatic automatically before starting Django
# Other services should NOT use this entrypoint

# Check if this is a Django runserver command
if echo "$*" | grep -q "manage.py runserver"; then
    # Wait for database to be ready
    echo "Waiting for database to be ready..."
    until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
        echo "Database is unavailable - sleeping"
        sleep 1
    done
    
    echo "Running migrations..."
    python manage.py migrate --noinput

    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

exec "$@"
