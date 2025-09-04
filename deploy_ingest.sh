#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Function to prompt for configuration
prompt_config() {
    local key=$1
    local prompt_text=$2
    local default_value=$3
    local current_value=""
    
    # Check if .env exists and get current value
    if [ -f .env ]; then
        current_value=$(grep "^$key=" .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' || echo "")
    fi
    
    if [ -n "$current_value" ]; then
        echo -n "$prompt_text [current: $current_value]: "
    else
        echo -n "$prompt_text [default: $default_value]: "
    fi
    
    read user_input
    
    if [ -z "$user_input" ]; then
        if [ -n "$current_value" ]; then
            echo "$current_value"
        else
            echo "$default_value"
        fi
    else
        echo "$user_input"
    fi
}

print_header "Ingest System Configuration"

# Create or update .env file
if [ -f .env ]; then
    print_warning ".env file exists. Using existing values or defaults."
else
    print_status "Creating new .env file..."
    touch .env
fi

# Use default configuration without prompting
print_status "Using default configuration values..."
POSTGRES_HOST="db"
POSTGRES_PORT="5432"
POSTGRES_DB="ingest"
POSTGRES_USER="ingest"
POSTGRES_PASSWORD="ingest123"

DJANGO_SECRET_KEY=$(openssl rand -base64 32 2>/dev/null || echo 'change-me-in-production')
ALLOWED_HOSTS="localhost,127.0.0.1"

MINIO_ENDPOINT="http://localhost:9000"
MINIO_ACCESS_KEY="minioadmin"
MINIO_SECRET_KEY="minioadmin"
MINIO_BUCKET_PRIVATE="ingest-private"

# Redis configuration
REDIS_HOST="redis"
REDIS_PORT="6379"

# Write .env file
print_status "Writing configuration to .env..."
cat > .env << EOF
# Database Configuration
POSTGRES_HOST=$POSTGRES_HOST
POSTGRES_PORT=$POSTGRES_PORT
POSTGRES_DB=$POSTGRES_DB
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# Django Configuration
DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY
ALLOWED_HOSTS=$ALLOWED_HOSTS
DEBUG=false

# MinIO Configuration (External)
MINIO_ENDPOINT=$MINIO_ENDPOINT
MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY
MINIO_SECRET_KEY=$MINIO_SECRET_KEY
MINIO_BUCKET_PRIVATE=$MINIO_BUCKET_PRIVATE

# Redis Configuration
REDIS_HOST=$REDIS_HOST
REDIS_PORT=$REDIS_PORT
REDIS_URL=redis://redis:6379/0

# Port Configuration
WEB_PORT=8001
DB_PORT=5434
REDIS_PORT=6379
EOF

# Check if MinIO is external (not localhost)
IS_EXTERNAL_MINIO=false
if [[ "$MINIO_ENDPOINT" != *"localhost"* ]] && [[ "$MINIO_ENDPOINT" != *"127.0.0.1"* ]]; then
    IS_EXTERNAL_MINIO=true
    print_status "External MinIO detected. Will skip MinIO container deployment."
fi

# Test MinIO connectivity
if [ "$IS_EXTERNAL_MINIO" = true ]; then
    print_status "Testing MinIO connectivity..."
    if curl -s -o /dev/null -w "%{http_code}" "$MINIO_ENDPOINT/minio/health/live" | grep -q "200"; then
        print_status "✅ MinIO endpoint is accessible"
    else
        print_warning "⚠️ MinIO health check failed - endpoint may be behind proxy"
    fi
fi

# Create docker-compose override for external MinIO
if [ "$IS_EXTERNAL_MINIO" = true ]; then
    print_status "Creating docker-compose override for external MinIO..."
    cat > docker-compose.override.yml << EOF
version: '3.8'

services:
  web:
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - MINIO_ENDPOINT=http://$MINIO_SERVER:9000

  worker:
    environment:
      - MINIO_ENDPOINT=http://$MINIO_SERVER:9000

  beat:
    environment:
      - MINIO_ENDPOINT=http://$MINIO_SERVER:9000

  # Remove MinIO services for external setup
  minio:
    deploy:
      replicas: 0
  
  createbuckets:
    deploy:
      replicas: 0
EOF
fi

print_header "Starting Services"

# Stop any existing containers
print_status "Stopping existing containers..."
docker-compose -f docker-compose.ingest.yml down

# Pull latest images
print_status "Pulling latest images..."
docker-compose -f docker-compose.ingest.yml pull

# Build application image
print_status "Building application image..."
docker-compose -f docker-compose.ingest.yml build

# Start services based on MinIO configuration
if [ "$IS_EXTERNAL_MINIO" = true ]; then
    print_status "Starting services with external MinIO..."
    docker-compose -f docker-compose.ingest.yml up -d db redis web worker beat
else
    print_status "Starting all services including MinIO..."
    docker-compose -f docker-compose.ingest.yml up -d
fi

print_header "Health Checks"

# Function to wait for service
wait_for_service() {
    local service_name=$1
    local health_check=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if eval $health_check > /dev/null 2>&1; then
            print_status "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start within expected time"
    return 1
}

# Wait for database
wait_for_service "PostgreSQL" "docker-compose -f docker-compose.ingest.yml exec -T db pg_isready -U ${POSTGRES_USER:-ingest}"

# Wait for Redis
wait_for_service "Redis" "docker-compose -f docker-compose.ingest.yml exec -T redis redis-cli ping"

# Wait for web application with multiple endpoint attempts
print_status "Waiting for Web Application to be ready..."
WEB_READY=false
for attempt in {1..30}; do
    if curl -s http://localhost:${WEB_PORT:-8001}/api/health/ > /dev/null 2>&1 || \
       curl -s http://localhost:${WEB_PORT:-8001}/health/ > /dev/null 2>&1 || \
       curl -s http://localhost:${WEB_PORT:-8001}/ > /dev/null 2>&1; then
        print_status "Web Application is ready! (attempt $attempt)"
        WEB_READY=true
        break
    fi
    echo -n "."
    sleep 3
done

if [ "$WEB_READY" = false ]; then
    print_warning "Web Application health check timeout, checking container status..."
    docker-compose -f docker-compose.ingest.yml logs web --tail 20
fi

# Check MinIO connectivity
if [ "$IS_EXTERNAL_MINIO" = true ]; then
    print_status "Testing external MinIO connectivity..."
    if curl -f http://$MINIO_SERVER:9000/minio/health/live > /dev/null 2>&1; then
        print_status "External MinIO is accessible"
    else
        print_warning "External MinIO health check failed. Please verify the server is running."
    fi
else
    wait_for_service "MinIO" "curl -f http://localhost:${MINIO_PORT:-9000}/minio/health/live"
fi

print_header "Service Status"

# Check service status
print_status "Checking service status..."
docker-compose -f docker-compose.ingest.yml ps

print_header "Running Initial Setup"

# Run database migrations
print_status "Running database migrations..."
docker-compose -f docker-compose.ingest.yml exec web python manage.py migrate

# Create superuser if needed
print_status "Creating superuser if absent..."
docker-compose -f docker-compose.ingest.yml exec web python manage.py create_superuser_if_absent

# Initialize roles and permissions
print_status "Initializing user roles and permissions..."
docker-compose -f docker-compose.ingest.yml exec web python manage.py init_roles

# Create sample data
print_status "Creating sample data..."
docker-compose -f docker-compose.ingest.yml exec web python manage.py seed_data

print_header "Final Health Check"

# Final comprehensive health check
services_status=()

# Check database
if docker-compose -f docker-compose.ingest.yml exec -T db pg_isready -U ${POSTGRES_USER:-ingest} > /dev/null 2>&1; then
    services_status+=("✅ PostgreSQL: Running")
else
    services_status+=("❌ PostgreSQL: Failed")
fi

# Check Redis
if docker-compose -f docker-compose.ingest.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    services_status+=("✅ Redis: Running")
else
    services_status+=("❌ Redis: Failed")
fi

# Check web application
if curl -s http://localhost:${WEB_PORT:-8001}/api/health/ > /dev/null 2>&1 || \
   curl -s http://localhost:${WEB_PORT:-8001}/health/ > /dev/null 2>&1 || \
   curl -s http://localhost:${WEB_PORT:-8001}/ > /dev/null 2>&1 || \
   docker-compose -f docker-compose.ingest.yml ps web | grep -q "Up"; then
    services_status+=(" Web Application: Running")
else
    services_status+=(" Web Application: Failed")
fi

# Check Celery worker
if docker-compose -f docker-compose.ingest.yml exec -T worker celery -A ingest inspect ping > /dev/null 2>&1; then
    services_status+=("✅ Celery Worker: Running")
else
    services_status+=("❌ Celery Worker: Failed")
fi

print_header "Deployment Summary"

echo "Service Status:"
for status in "${services_status[@]}"; do
    echo "  $status"
done

echo ""
print_header "Access Links"

echo "🌐 Web Services:
  📊 Admin Interface:     http://localhost:${WEB_PORT:-8001}/admin/
  📋 API Documentation:  http://localhost:${WEB_PORT:-8001}/api/schema/swagger-ui/
  📖 ReDoc:              http://localhost:${WEB_PORT:-8001}/api/schema/redoc/
  🔍 Health Check:       http://localhost:${WEB_PORT:-8001}/api/health/"
echo ""

if [ "$IS_EXTERNAL_MINIO" = true ]; then
    echo "🗄️  External Storage:"
    echo "  📦 MinIO API:          http://$MINIO_SERVER:9000/"
    echo "  🎛️  MinIO Console:      http://$MINIO_SERVER:9001/"
else
    echo "🗄️  Storage Services:"
    echo "  📦 MinIO API:          http://localhost:${MINIO_PORT:-9000}/"
    echo "  🎛️  MinIO Console:      http://localhost:${MINIO_CONSOLE_PORT:-9001}/"
fi

echo ""
echo "🔐 Default Credentials:"
echo "  👤 Admin User:         admin / admin123"
echo "  🗄️  MinIO:              ${MINIO_ACCESS_KEY:-minioadmin} / ${MINIO_SECRET_KEY:-minioadmin}"
echo ""

print_header "Quick Commands"

echo "📝 Useful Commands:"
echo "  docker-compose -f docker-compose.ingest.yml logs web          # View application logs"
echo "  docker-compose -f docker-compose.ingest.yml logs worker       # View worker logs"
echo "  docker-compose -f docker-compose.ingest.yml exec web bash     # Access web container"
echo "  docker-compose restart web       # Restart web service"
echo "  docker-compose -f docker-compose.ingest.yml down              # Stop all services"
echo ""

# Check for any failed services
failed_services=$(printf '%s\n' "${services_status[@]}" | grep -c "❌" || true)

if [ "$failed_services" -gt 0 ]; then
    print_error "⚠️  $failed_services service(s) failed to start properly."
    print_error "Please check the logs: docker-compose -f docker-compose.ingest.yml logs"
    exit 1
else
    print_status "🎉 All services are running successfully!"
    print_status "🚀 Ingest system is ready for use!"
fi

# Clean up override file if created
if [ -f docker-compose.override.yml ] && [ "$IS_EXTERNAL_MINIO" = false ]; then
    rm docker-compose.override.yml
fi
