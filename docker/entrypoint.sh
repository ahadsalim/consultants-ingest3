#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 0.1
done
echo "Database started"

# Run prestart script
echo "Running prestart script..."
/prestart.sh

# Execute the main command
exec "$@"
