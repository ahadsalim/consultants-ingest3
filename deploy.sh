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

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from .env.example..."
    cp .env.example .env
    print_status ".env file created. Please review and update the configuration."
fi

# Load environment variables
source .env

print_header "Ingest System Deployment"

# Get MinIO server address
print_status "Configuring MinIO connection..."
echo -n "Enter MinIO server address (press Enter for localhost): "
read MINIO_SERVER

if [ -z "$MINIO_SERVER" ]; then
    MINIO_SERVER="localhost"
    print_status "Using localhost for MinIO server"
else
    print_status "Using MinIO server: $MINIO_SERVER"
    
    # Update .env file with external MinIO server
    sed -i "s|MINIO_ENDPOINT=.*|MINIO_ENDPOINT=http://$MINIO_SERVER:9000|g" .env
    print_status "Updated .env with MinIO server address"
fi

# Check if MinIO is external (not localhost)
IS_EXTERNAL_MINIO=false
if [ "$MINIO_SERVER" != "localhost" ] && [ "$MINIO_SERVER" != "127.0.0.1" ]; then
    IS_EXTERNAL_MINIO=true
    print_status "External MinIO detected. Will skip MinIO container deployment."
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
docker-compose down

# Pull latest images
print_status "Pulling latest images..."
docker-compose pull

# Build application image
print_status "Building application image..."
docker-compose build

# Start services based on MinIO configuration
if [ "$IS_EXTERNAL_MINIO" = true ]; then
    print_status "Starting services with external MinIO..."
    docker-compose up -d db redis web worker beat
else
    print_status "Starting all services including MinIO..."
    docker-compose up -d
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
wait_for_service "PostgreSQL" "docker-compose exec -T db pg_isready -U ${POSTGRES_USER:-ingest}"

# Wait for Redis
wait_for_service "Redis" "docker-compose exec -T redis redis-cli ping"

# Wait for web application
wait_for_service "Web Application" "curl -f http://localhost:${WEB_PORT:-8000}/api/health/"

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
docker-compose ps

print_header "Running Initial Setup"

# Run database migrations
print_status "Running database migrations..."
docker-compose exec web python manage.py migrate

# Create superuser if needed
print_status "Creating superuser if absent..."
docker-compose exec web python manage.py create_superuser_if_absent

# Initialize roles and permissions
print_status "Initializing user roles and permissions..."
docker-compose exec web python manage.py init_roles

# Create sample data
print_status "Creating sample data..."
docker-compose exec web python manage.py seed_data

print_header "Final Health Check"

# Final comprehensive health check
services_status=()

# Check database
if docker-compose exec -T db pg_isready -U ${POSTGRES_USER:-ingest} > /dev/null 2>&1; then
    services_status+=("✅ PostgreSQL: Running")
else
    services_status+=("❌ PostgreSQL: Failed")
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    services_status+=("✅ Redis: Running")
else
    services_status+=("❌ Redis: Failed")
fi

# Check web application
if curl -f http://localhost:${WEB_PORT:-8000}/api/health/ > /dev/null 2>&1; then
    services_status+=("✅ Web Application: Running")
else
    services_status+=("❌ Web Application: Failed")
fi

# Check MinIO
if [ "$IS_EXTERNAL_MINIO" = true ]; then
    if curl -f http://$MINIO_SERVER:9000/minio/health/live > /dev/null 2>&1; then
        services_status+=("✅ MinIO (External): Running")
    else
        services_status+=("❌ MinIO (External): Failed")
    fi
else
    if curl -f http://localhost:${MINIO_PORT:-9000}/minio/health/live > /dev/null 2>&1; then
        services_status+=("✅ MinIO: Running")
    else
        services_status+=("❌ MinIO: Failed")
    fi
fi

# Check Celery worker
if docker-compose exec -T worker celery -A ingest inspect ping > /dev/null 2>&1; then
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

echo "🌐 Web Services:"
echo "  📊 Admin Interface:     http://localhost:${WEB_PORT:-8000}/admin/"
echo "  📋 API Documentation:  http://localhost:${WEB_PORT:-8000}/api/schema/swagger-ui/"
echo "  📖 ReDoc:              http://localhost:${WEB_PORT:-8000}/api/schema/redoc/"
echo "  🔍 Health Check:       http://localhost:${WEB_PORT:-8000}/api/health/"
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
echo "  docker-compose logs web          # View application logs"
echo "  docker-compose logs worker       # View worker logs"
echo "  docker-compose exec web bash     # Access web container"
echo "  docker-compose restart web       # Restart web service"
echo "  docker-compose down              # Stop all services"
echo ""

# Check for any failed services
failed_services=$(printf '%s\n' "${services_status[@]}" | grep -c "❌" || true)

if [ "$failed_services" -gt 0 ]; then
    print_error "⚠️  $failed_services service(s) failed to start properly."
    print_error "Please check the logs: docker-compose logs"
    exit 1
else
    print_status "🎉 All services are running successfully!"
    print_status "🚀 Ingest system is ready for use!"
fi

# Clean up override file if created
if [ -f docker-compose.override.yml ] && [ "$IS_EXTERNAL_MINIO" = false ]; then
    rm docker-compose.override.yml
fi
