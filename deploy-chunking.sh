#!/bin/bash

# Deployment script for chunking and embedding system
set -e

echo "🚀 Deploying Chunking and Embedding System"
echo "=========================================="

# Step 1: Install ML dependencies
echo "📦 Installing ML dependencies..."
docker-compose -f docker-compose.ingest.yml exec web pip install sentence-transformers==2.2.2 transformers==4.35.2 torch==2.1.1

# Step 2: Generate migrations
echo "🔄 Generating database migrations..."
docker-compose -f docker-compose.ingest.yml exec web python manage.py makemigrations documents

# Step 3: Apply migrations
echo "📊 Applying database migrations..."
docker-compose -f docker-compose.ingest.yml exec web python manage.py migrate

# Step 4: Test the system
echo "🧪 Testing chunking system..."
docker-compose -f docker-compose.ingest.yml exec web python manage.py process_chunks --cleanup-duplicates

echo "✅ Chunking system deployed successfully!"
echo ""
echo "📋 Available commands:"
echo "  # Process all expressions:"
echo "  docker-compose -f docker-compose.ingest.yml exec web python manage.py process_chunks --all"
echo ""
echo "  # Process specific expression:"
echo "  docker-compose -f docker-compose.ingest.yml exec web python manage.py process_chunks --expression-id <uuid>"
echo ""
echo "  # Process specific legal unit:"
echo "  docker-compose -f docker-compose.ingest.yml exec web python manage.py process_chunks --unit-id <uuid>"
echo ""
echo "  # Clean up duplicates:"
echo "  docker-compose -f docker-compose.ingest.yml exec web python manage.py process_chunks --cleanup-duplicates"
echo ""
echo "🎉 System is ready! Automatic chunking will now trigger when legal units are uploaded."
