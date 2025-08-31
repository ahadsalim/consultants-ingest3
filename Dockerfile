FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=ingest.settings.prod

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        curl \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy prestart script
COPY docker/prestart.sh /prestart.sh
RUN chmod +x /prestart.sh

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app

# Create staticfiles directory with proper permissions
RUN mkdir -p /app/staticfiles
RUN chown -R appuser:appuser /app/staticfiles
RUN chmod -R 755 /app/staticfiles

USER appuser

# Expose port
EXPOSE 8000

# Run entrypoint
ENTRYPOINT ["/entrypoint.sh"]
