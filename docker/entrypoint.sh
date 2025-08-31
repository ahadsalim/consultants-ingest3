#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
python -c "
import os
import time
import sys

try:
    import psycopg2
except ImportError:
    import psycopg

host = os.environ.get('POSTGRES_HOST', 'db')
port = 5432  # Internal Docker port, not external mapped port
user = os.environ.get('POSTGRES_USER', 'ingest')
password = os.environ.get('POSTGRES_PASSWORD', 'password')
db = os.environ.get('POSTGRES_DB', 'ingest')

max_attempts = 300  # 30 seconds
attempt = 0

while attempt < max_attempts:
    try:
        if 'psycopg2' in sys.modules:
            import psycopg2
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=db,
                connect_timeout=1
            )
        else:
            import psycopg
            conn = psycopg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=db,
                connect_timeout=1
            )
        conn.close()
        print('Database connection successful')
        sys.exit(0)
    except Exception as e:
        print(f'Attempt {attempt + 1}: {e}')
        time.sleep(0.1)
        attempt += 1

print('Database connection failed after 30 seconds')
sys.exit(1)
"
echo "Database started"

# Run prestart script
echo "Running prestart script..."
/prestart.sh

# Execute the main command
exec "$@"
