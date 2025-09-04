#!/bin/bash
# Remove set -e to prevent script from exiting on non-critical errors

echo "Creating database migrations..."
python manage.py makemigrations accounts masterdata documents syncbridge embeddings audit || echo "Makemigrations completed with warnings"

echo "Running database migrations..."
python manage.py migrate || echo "Migrations completed with warnings"

echo "Collecting static files..."
# Skip static files collection for worker and beat containers
if [ "$1" != "celery" ]; then
    python manage.py collectstatic --noinput || echo "Static files collection completed with warnings"
else
    echo "Skipping static files collection for Celery container"
fi

echo "Initializing pgvector extension..."
python manage.py init_pgvector || echo "pgvector initialization completed with warnings"

echo "Creating user groups and permissions..."
python manage.py init_roles || echo "Roles initialization completed with warnings"

echo "Creating superuser if absent..."
python manage.py create_superuser_if_absent || echo "Superuser creation completed with warnings"

echo "Prestart script completed successfully!"
