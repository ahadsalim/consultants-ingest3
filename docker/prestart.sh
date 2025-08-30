#!/bin/bash
set -e

echo "Creating database migrations..."
python manage.py makemigrations accounts masterdata documents syncbridge embeddings audit

echo "Running database migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Initializing pgvector extension..."
python manage.py init_pgvector

echo "Creating user groups and permissions..."
python manage.py init_roles

echo "Creating superuser if absent..."
python manage.py create_superuser_if_absent

echo "Prestart script completed successfully!"
